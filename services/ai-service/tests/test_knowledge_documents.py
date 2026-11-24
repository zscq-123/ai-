import base64
import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient

from ai_service.api.knowledge_documents import search_uploaded_knowledge
from ai_service.config import settings
from ai_service.main import app


@pytest.fixture(autouse=True)
def isolated_knowledge_state(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "mailbox_state_file", str(tmp_path / "mailboxes.json"))
    monkeypatch.setattr(settings, "buzud_knowledge_root", "")


def encoded(content: bytes) -> str:
    return base64.b64encode(content).decode()


def test_upload_list_toggle_and_search_markdown(tmp_path) -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/knowledge/documents",
        json={
            "name": "售后规则.md",
            "content_base64": encoded("退款申请需要提供订单号和商品照片。".encode()),
            "content_type": "text/markdown",
            "category": "store",
        },
    )

    assert response.status_code == 201
    document = response.json()
    assert document["format"] == "MD"
    assert document["enabled"] is True
    assert document["extracted_chars"] > 0
    assert (tmp_path / "knowledge-documents.json").stat().st_mode & 0o777 == 0o600
    assert list((tmp_path / "knowledge-files").glob("*.md"))

    listed = client.get("/v1/knowledge/documents")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [document["id"]]

    detail = client.get(f"/v1/knowledge/documents/{document['id']}")
    assert detail.status_code == 200
    assert "退款申请需要提供订单号" in detail.json()["preview"]
    assert detail.json()["preview_truncated"] is False

    evidence = search_uploaded_knowledge("退款需要什么材料")
    assert evidence
    assert "订单号" in str(evidence[0]["content"])
    assert str(evidence[0]["reference"]).startswith("faq://buzud/upload-doc-")

    disabled = client.patch(
        f"/v1/knowledge/documents/{document['id']}", json={"enabled": False}
    )
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False
    assert search_uploaded_knowledge("退款需要什么材料") == []
    deleted = client.delete(f"/v1/knowledge/documents/{document['id']}")
    assert deleted.status_code == 204
    assert client.get("/v1/knowledge/documents").json() == []


def test_upload_extracts_docx_text() -> None:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(
            "word/document.xml",
            """<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>血糖监测产品说明</w:t></w:r></w:p><w:p><w:r><w:t>传感器需按说明书佩戴。</w:t></w:r></w:p></w:body></w:document>""",
        )

    response = TestClient(app).post(
        "/v1/knowledge/documents",
        json={
            "name": "产品说明.docx",
            "content_base64": encoded(stream.getvalue()),
            "content_type": (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
            "category": "store",
        },
    )

    assert response.status_code == 201
    assert response.json()["format"] == "DOCX"
    assert search_uploaded_knowledge("传感器怎么佩戴")


def test_upload_extracts_xlsx_rows() -> None:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(
            "xl/sharedStrings.xml",
            """<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>商品</t></si><si><t>价格</t></si><si><t>血糖仪</t></si></sst>""",
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            """<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
            <sheetData>
              <row r="1"><c t="s"><v>0</v></c><c t="s"><v>1</v></c></row>
              <row r="2"><c t="s"><v>2</v></c><c><v>495.90</v></c></row>
            </sheetData></worksheet>""",
        )

    response = TestClient(app).post(
        "/v1/knowledge/documents",
        json={
            "name": "商品价格.xlsx",
            "content_base64": encoded(stream.getvalue()),
            "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "category": "store",
        },
    )

    assert response.status_code == 201
    assert response.json()["rows"] == 2
    assert search_uploaded_knowledge("血糖仪价格")


def test_rejects_unsupported_and_duplicate_files() -> None:
    client = TestClient(app)
    unsupported = client.post(
        "/v1/knowledge/documents",
        json={"name": "archive.zip", "content_base64": encoded(b"zip")},
    )
    assert unsupported.status_code == 415

    payload = {"name": "faq.txt", "content_base64": encoded("常见问题".encode())}
    assert client.post("/v1/knowledge/documents", json=payload).status_code == 201
    duplicate = client.post("/v1/knowledge/documents", json=payload)
    assert duplicate.status_code == 409


def test_lists_connected_buzud_faq_categories_and_products(monkeypatch, tmp_path) -> None:
    (tmp_path / "chat-knowledge.json").write_text(
        json.dumps(
            {
                "rules": [
                    {
                        "id": "contact",
                        "keywords": ["客服", "邮箱"],
                        "reply": "客服邮箱 customerservice@chungyip.com。",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (tmp_path / "catalog.json").write_text(
        json.dumps(
            {
                "catalogCategories": [
                    {
                        "id": "glucose",
                        "name": "血糖监测",
                        "products": [
                            {
                                "id": "888",
                                "name": "BUZUD CGMS",
                                "productType": "动态血糖监测系统",
                                "price": 495.9,
                                "detail": {"intendedFor": "适合需要连续监测的用户。"},
                            }
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "buzud_knowledge_root", str(tmp_path))

    response = TestClient(app).get("/v1/knowledge/connected")

    assert response.status_code == 200
    payload = response.json()
    assert [item["kind"] for item in payload] == ["faq", "category", "product"]
    assert payload[0]["title"] == "客服邮箱与联系方式"
    assert payload[1]["item_count"] == 1
    assert payload[2]["summary"].startswith("SGD 495.90")
