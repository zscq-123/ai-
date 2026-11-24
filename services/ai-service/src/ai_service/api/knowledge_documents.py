import base64
import binascii
import contextlib
import csv
import hashlib
import io
import json
import re
import threading
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4
from xml.etree import ElementTree

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from ai_service.config import settings

router = APIRouter(prefix="/v1/knowledge", tags=["knowledge"])

Category = Literal["store", "platform"]
DocumentStatus = Literal["ready", "needs_attention"]
SourceType = Literal["document", "table"]
ConnectedKnowledgeKind = Literal["faq", "category", "product"]

MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_EXTRACTED_CHARS = 2_000_000
MAX_DOCUMENTS = 200
ALLOWED_EXTENSIONS = {".docx", ".xlsx", ".csv", ".tsv", ".md", ".txt"}
TABLE_EXTENSIONS = {".xlsx", ".csv", ".tsv"}


class KnowledgeUploadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=240)
    content_base64: str = Field(min_length=1, max_length=12_000_000)
    content_type: str = Field(default="application/octet-stream", max_length=160)
    category: Category = "store"


class KnowledgeDocumentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


class KnowledgeDocument(BaseModel):
    id: str
    name: str
    title: str
    category: Category
    source_type: SourceType
    format: str
    content_type: str
    size_bytes: int
    extracted_chars: int
    rows: int | None = None
    enabled: bool
    status: DocumentStatus
    uploaded_at: datetime


class KnowledgeDocumentDetail(KnowledgeDocument):
    preview: str
    preview_truncated: bool


class StoredKnowledgeDocument(KnowledgeDocument):
    checksum: str
    extension: str


class ConnectedKnowledgeItem(BaseModel):
    id: str
    title: str
    kind: ConnectedKnowledgeKind
    source: str
    summary: str
    keywords: list[str]
    item_count: int | None = None
    updated_at: datetime


_state_lock = threading.RLock()


def _state_root() -> Path:
    configured = settings.mailbox_state_file.strip()
    if configured:
        return Path(configured).expanduser().parent
    return Path.home() / ".local" / "share" / "nova-ai-service"


def _metadata_path() -> Path:
    return _state_root() / "knowledge-documents.json"


def _files_path() -> Path:
    return _state_root() / "knowledge-files"


def _buzud_root() -> Path | None:
    configured = settings.buzud_knowledge_root.strip()
    return Path(configured).expanduser() if configured else None


def _read_json(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (FileNotFoundError, OSError, ValueError, TypeError):
        return {}


def _knowledge_updated_at(*paths: Path) -> datetime:
    timestamps = [path.stat().st_mtime for path in paths if path.exists()]
    return datetime.fromtimestamp(max(timestamps), UTC) if timestamps else datetime.now(UTC)


FAQ_TITLES = {
    "delivery": "配送时效与物流说明",
    "aftersales": "维修、退换货与售后规则",
    "stores": "新加坡体验门店地址",
    "warranty": "产品保修登记与服务",
    "contact": "客服邮箱与联系方式",
    "products": "商城产品范围与认证说明",
    "greeting": "客服欢迎语与咨询范围",
}


def _connected_knowledge() -> list[ConnectedKnowledgeItem]:
    root = _buzud_root()
    if root is None:
        return []
    faq_path = root / "chat-knowledge.json"
    catalog_path = root / "catalog.json"
    faq = _read_json(faq_path)
    catalog = _read_json(catalog_path)
    updated_at = _knowledge_updated_at(faq_path, catalog_path)
    result: list[ConnectedKnowledgeItem] = []
    rules = faq.get("rules", [])
    if isinstance(rules, list):
        for raw in rules:
            if not isinstance(raw, dict):
                continue
            rule_id = str(raw.get("id") or "").strip()
            reply = str(raw.get("reply") or "").strip()
            keywords = [str(item) for item in raw.get("keywords", []) if str(item).strip()]
            if not rule_id or not reply:
                continue
            result.append(
                ConnectedKnowledgeItem(
                    id=f"buzud-faq-{rule_id}",
                    title=FAQ_TITLES.get(rule_id, rule_id),
                    kind="faq",
                    source="CHUNG YIP 商城 · 客服规则",
                    summary=reply[:500],
                    keywords=keywords[:32],
                    updated_at=updated_at,
                )
            )
    categories = catalog.get("catalogCategories", [])
    if not isinstance(categories, list):
        return result
    unique_products: dict[str, tuple[dict[str, object], str]] = {}
    for raw_category in categories:
        if not isinstance(raw_category, dict):
            continue
        category_id = str(raw_category.get("id") or "").strip()
        name = str(raw_category.get("name") or category_id).strip()
        products = raw_category.get("products", [])
        product_items = (
            [item for item in products if isinstance(item, dict)]
            if isinstance(products, list)
            else []
        )
        if category_id and name:
            result.append(
                ConnectedKnowledgeItem(
                    id=f"buzud-category-{category_id}",
                    title=name,
                    kind="category",
                    source="CHUNG YIP 商城 · 商品分类",
                    summary=f"该分类当前同步 {len(product_items)} 款商品资料。",
                    keywords=[name],
                    item_count=len(product_items),
                    updated_at=updated_at,
                )
            )
        for raw_product in product_items:
            product_id = str(raw_product.get("id") or "").strip()
            if product_id:
                unique_products[product_id] = (raw_product, name)
    for product_id, (raw_product, category_name) in unique_products.items():
        name = str(raw_product.get("name") or product_id).strip()
        product_type = str(raw_product.get("productType") or category_name).strip()
        price = raw_product.get("price")
        price_text = (
            f"SGD {float(price):.2f}"
            if isinstance(price, int | float)
            else "价格以商品页为准"
        )
        detail = raw_product.get("detail")
        detail_payload = detail if isinstance(detail, dict) else {}
        description = str(
            detail_payload.get("description")
            or detail_payload.get("intendedFor")
            or "商品规格、用法与注意事项以商城详情页为准。"
        ).strip()
        result.append(
            ConnectedKnowledgeItem(
                id=f"buzud-product-{product_id}",
                title=name,
                kind="product",
                source=f"CHUNG YIP 商城 · {category_name}",
                summary=f"{price_text} · {description}"[:500],
                keywords=list(dict.fromkeys([name, product_type, category_name]))[:32],
                updated_at=updated_at,
            )
        )
    return result


def _load_documents() -> list[StoredKnowledgeDocument]:
    try:
        payload = json.loads(_metadata_path().read_text(encoding="utf-8"))
        return [StoredKnowledgeDocument.model_validate(item) for item in payload]
    except (FileNotFoundError, OSError, ValueError, TypeError):
        return []


def _persist_documents(documents: list[StoredKnowledgeDocument]) -> None:
    path = _metadata_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(
            [document.model_dump(mode="json") for document in documents],
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    temporary.chmod(0o600)
    temporary.replace(path)


def _public(document: StoredKnowledgeDocument) -> KnowledgeDocument:
    return KnowledgeDocument.model_validate(
        document.model_dump(exclude={"checksum", "extension"})
    )


def _decode_text(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise HTTPException(status_code=422, detail="文件文字编码无法识别，请另存为 UTF-8 后重试")


def _validate_zip(archive: zipfile.ZipFile) -> None:
    files = archive.infolist()
    if len(files) > 1_000 or sum(item.file_size for item in files) > 50 * 1024 * 1024:
        raise HTTPException(status_code=422, detail="文档解压后的内容过大")
    if any(item.file_size > 20 * 1024 * 1024 for item in files):
        raise HTTPException(status_code=422, detail="文档包含异常大的内部文件")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _extract_docx(content: bytes) -> tuple[str, int | None]:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            _validate_zip(archive)
            root = ElementTree.fromstring(archive.read("word/document.xml"))
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as exc:
        raise HTTPException(status_code=422, detail="Word 文档已损坏或格式不受支持") from exc
    paragraphs: list[str] = []
    for paragraph in (node for node in root.iter() if _local_name(node.tag) == "p"):
        text = "".join(
            node.text or "" for node in paragraph.iter() if _local_name(node.tag) == "t"
        ).strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs), None


def _cell_value(cell: ElementTree.Element, shared: list[str]) -> str:
    kind = cell.attrib.get("t")
    if kind == "inlineStr":
        return "".join(
            node.text or "" for node in cell.iter() if _local_name(node.tag) == "t"
        )
    value = next(
        (node.text or "" for node in cell.iter() if _local_name(node.tag) == "v"),
        "",
    )
    if kind == "s" and value.isdigit() and int(value) < len(shared):
        return shared[int(value)]
    return value


def _extract_xlsx(content: bytes) -> tuple[str, int | None]:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            _validate_zip(archive)
            names = set(archive.namelist())
            shared: list[str] = []
            if "xl/sharedStrings.xml" in names:
                shared_root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
                shared = [
                    "".join(
                        child.text or ""
                        for child in node.iter()
                        if _local_name(child.tag) == "t"
                    )
                    for node in shared_root.iter()
                    if _local_name(node.tag) == "si"
                ]
            rows: list[str] = []
            worksheet_names = sorted(
                name
                for name in names
                if name.startswith("xl/worksheets/") and name.endswith(".xml")
            )
            for worksheet_name in worksheet_names:
                root = ElementTree.fromstring(archive.read(worksheet_name))
                for row in (node for node in root.iter() if _local_name(node.tag) == "row"):
                    values = [
                        _cell_value(cell, shared)
                        for cell in row
                        if _local_name(cell.tag) == "c"
                    ]
                    if any(value.strip() for value in values):
                        rows.append("\t".join(values))
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as exc:
        raise HTTPException(status_code=422, detail="Excel 表格已损坏或格式不受支持") from exc
    return "\n".join(rows), len(rows)


def _extract_delimited(content: bytes, delimiter: str) -> tuple[str, int | None]:
    text = _decode_text(content)
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    normalized = ["\t".join(value.strip() for value in row) for row in rows if any(row)]
    return "\n".join(normalized), len(normalized)


def _extract(content: bytes, extension: str) -> tuple[str, int | None]:
    if extension == ".docx":
        return _extract_docx(content)
    if extension == ".xlsx":
        return _extract_xlsx(content)
    if extension == ".csv":
        return _extract_delimited(content, ",")
    if extension == ".tsv":
        return _extract_delimited(content, "\t")
    return _decode_text(content), None


def _normalize_text(text: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)[:MAX_EXTRACTED_CHARS]


def _write_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.chmod(0o600)
    temporary.replace(path)


@router.get("/documents", response_model=list[KnowledgeDocument])
def list_knowledge_documents() -> list[KnowledgeDocument]:
    with _state_lock:
        return [_public(document) for document in reversed(_load_documents())]


@router.get("/documents/{document_id}", response_model=KnowledgeDocumentDetail)
def get_knowledge_document(document_id: str) -> KnowledgeDocumentDetail:
    with _state_lock:
        document = next(
            (item for item in _load_documents() if item.id == document_id),
            None,
        )
        if document is None:
            raise HTTPException(status_code=404, detail="知识文件不存在")
        try:
            content = (_files_path() / f"{document.id}.txt").read_text(encoding="utf-8")
        except OSError as exc:
            raise HTTPException(status_code=409, detail="知识文件的解析内容不可用") from exc
    preview_limit = 20_000
    return KnowledgeDocumentDetail.model_validate(
        {
            **_public(document).model_dump(),
            "preview": content[:preview_limit],
            "preview_truncated": len(content) > preview_limit,
        }
    )


@router.get("/connected", response_model=list[ConnectedKnowledgeItem])
def list_connected_knowledge() -> list[ConnectedKnowledgeItem]:
    return _connected_knowledge()


@router.post(
    "/documents",
    response_model=KnowledgeDocument,
    status_code=status.HTTP_201_CREATED,
)
def upload_knowledge_document(payload: KnowledgeUploadRequest) -> KnowledgeDocument:
    if Path(payload.name).name != payload.name:
        raise HTTPException(status_code=422, detail="文件名不合法")
    extension = Path(payload.name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail="支持 DOCX、XLSX、CSV、TSV、Markdown 和 TXT 文件",
        )
    try:
        content = base64.b64decode(payload.content_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=422, detail="文件内容编码无效") from exc
    if not content:
        raise HTTPException(status_code=422, detail="不能上传空文件")
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="单个文件不能超过 8 MB")
    extracted, rows = _extract(content, extension)
    normalized = _normalize_text(extracted)
    if not normalized:
        raise HTTPException(status_code=422, detail="文件中没有可导入的文字或表格内容")
    checksum = hashlib.sha256(content).hexdigest()
    with _state_lock:
        documents = _load_documents()
        if len(documents) >= MAX_DOCUMENTS:
            raise HTTPException(status_code=409, detail="知识文件数量已达到 200 个上限")
        if any(document.checksum == checksum for document in documents):
            raise HTTPException(status_code=409, detail="该文件已经上传过")
        document_id = f"doc-{uuid4().hex[:16]}"
        _write_file(_files_path() / f"{document_id}{extension}", content)
        _write_file(_files_path() / f"{document_id}.txt", normalized.encode("utf-8"))
        document = StoredKnowledgeDocument(
            id=document_id,
            name=payload.name,
            title=Path(payload.name).stem[:120],
            category=payload.category,
            source_type="table" if extension in TABLE_EXTENSIONS else "document",
            format=extension.removeprefix(".").upper(),
            content_type=payload.content_type,
            size_bytes=len(content),
            extracted_chars=len(normalized),
            rows=rows,
            enabled=True,
            status="ready",
            uploaded_at=datetime.now(UTC),
            checksum=checksum,
            extension=extension,
        )
        documents.append(document)
        _persist_documents(documents)
        return _public(document)


@router.patch("/documents/{document_id}", response_model=KnowledgeDocument)
def update_knowledge_document(
    document_id: str, payload: KnowledgeDocumentUpdate
) -> KnowledgeDocument:
    with _state_lock:
        documents = _load_documents()
        index = next(
            (index for index, document in enumerate(documents) if document.id == document_id),
            None,
        )
        if index is None:
            raise HTTPException(status_code=404, detail="知识文件不存在")
        documents[index] = documents[index].model_copy(update={"enabled": payload.enabled})
        _persist_documents(documents)
        return _public(documents[index])


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_knowledge_document(document_id: str) -> None:
    with _state_lock:
        documents = _load_documents()
        document = next(
            (document for document in documents if document.id == document_id),
            None,
        )
        if document is None:
            raise HTTPException(status_code=404, detail="知识文件不存在")
        _persist_documents([item for item in documents if item.id != document_id])
        for path in (
            _files_path() / f"{document.id}{document.extension}",
            _files_path() / f"{document.id}.txt",
        ):
            with contextlib.suppress(FileNotFoundError):
                path.unlink()


def _query_terms(query: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", query.lower()).strip()
    terms = re.findall(r"[a-z0-9][a-z0-9_-]{1,30}", normalized)
    chinese = "".join(re.findall(r"[\u4e00-\u9fff]", normalized))
    terms.extend(chinese[index : index + 2] for index in range(max(0, len(chinese) - 1)))
    if len(normalized) >= 2:
        terms.insert(0, normalized)
    return list(dict.fromkeys(term for term in terms if len(term) >= 2))[:32]


def _excerpt(text: str, terms: list[str]) -> str:
    lower = text.lower()
    positions = [lower.find(term) for term in terms if lower.find(term) >= 0]
    if not positions:
        return text[:4_000]
    start = max(0, min(positions) - 600)
    return text[start : start + 4_000]


def search_uploaded_knowledge(query: str, limit: int = 4) -> list[dict[str, object]]:
    terms = _query_terms(query)
    if not terms:
        return []
    scored: list[tuple[int, StoredKnowledgeDocument, str, list[str]]] = []
    with _state_lock:
        documents = _load_documents()
    for document in documents:
        if not document.enabled or document.status != "ready":
            continue
        try:
            text = (_files_path() / f"{document.id}.txt").read_text(encoding="utf-8")
        except OSError:
            continue
        title = document.title.lower()
        lower = text.lower()
        matched = [term for term in terms if term in title or term in lower]
        if not matched:
            continue
        score = sum(8 if term in title else min(lower.count(term), 4) for term in matched)
        scored.append((score, document, text, matched))
    scored.sort(key=lambda item: (item[0], item[1].uploaded_at), reverse=True)
    return [
        {
            "content": _excerpt(text, matched),
            "title": document.title,
            "reference": f"faq://buzud/upload-{document.id}",
            "keywords": matched,
        }
        for _, document, text, matched in scored[:limit]
    ]
