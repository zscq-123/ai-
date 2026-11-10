import pytest

from ai_service.domain.models import Citation
from ai_service.infrastructure.local_knowledge import (
    LocalKnowledgeRetriever,
    load_entries,
)


@pytest.fixture
def retriever() -> LocalKnowledgeRetriever:
    return LocalKnowledgeRetriever()


async def test_greeting_returns_no_documents(retriever: LocalKnowledgeRetriever) -> None:
    assert await retriever.search("你好") == []


async def test_delivery_question_matches_delivery_policy(
    retriever: LocalKnowledgeRetriever,
) -> None:
    results = await retriever.search("多久发货？")

    assert results
    content, citation = results[0]
    assert "出库" in content
    assert citation.reference == "policy://delivery"


@pytest.mark.parametrize(
    ("question", "reference"),
    (
        ("黑色XL现在有现货吗？", "policy://inventory"),
        ("可以用花呗分期吗？", "policy://payment"),
    ),
)
async def test_fact_sensitive_question_finds_generic_policy(
    retriever: LocalKnowledgeRetriever, question: str, reference: str
) -> None:
    results = await retriever.search(question)

    assert results
    assert results[0][1].reference == reference


@pytest.mark.parametrize(
    ("question", "reference"),
    (
        ("货一直没动", "policy://logistics"),
        ("这个支持白条吗", "policy://payment"),
        ("包装拆了还能退不", "policy://return"),
        ("尺码不合适咋整", "policy://exchange"),
        ("你们是官方直营吗", "policy://marketplace"),
    ),
)
async def test_colloquial_queries_find_the_right_policy(
    retriever: LocalKnowledgeRetriever, question: str, reference: str
) -> None:
    results = await retriever.search(question, limit=1)

    assert results
    assert results[0][1].reference == reference


async def test_unrelated_question_returns_no_documents(
    retriever: LocalKnowledgeRetriever,
) -> None:
    assert await retriever.search("帮我查一下别人的订单") == []


async def test_zero_overlap_query_is_filtered_out(retriever: LocalKnowledgeRetriever) -> None:
    assert await retriever.search("今天天气怎么样") == []


async def test_results_respect_limit(retriever: LocalKnowledgeRetriever) -> None:
    results = await retriever.search("商品发货后物流多久到，能开发票吗，可以退货吗", limit=2)

    assert len(results) <= 2


async def test_explicit_keyword_omits_bigram_only_neighbors(
    retriever: LocalKnowledgeRetriever,
) -> None:
    results = await retriever.search("退货后退款多久到账", limit=4)

    assert [citation.reference for _, citation in results] == [
        "policy://refund",
        "policy://return",
    ]


async def test_bigram_fallback_returns_only_one_document(
    retriever: LocalKnowledgeRetriever,
) -> None:
    results = await retriever.search("这件东西是哪家在卖", limit=4)

    assert len(results) <= 1


async def test_bigram_fallback_can_be_disabled() -> None:
    retriever = LocalKnowledgeRetriever(allow_bigram_fallback=False)

    assert await retriever.search("这件东西是哪家在卖") == []


async def test_common_input_typo_is_normalized(
    retriever: LocalKnowledgeRetriever,
) -> None:
    results = await retriever.search("这款的才质是什么", limit=1)

    assert results[0][1].reference == "policy://product-spec"


async def test_custom_entries_can_replace_defaults() -> None:
    entry = ("自定义知识内容", Citation("自定义", "kb://custom"), ("自定义",))
    from ai_service.infrastructure.local_knowledge import KnowledgeEntry

    retriever = LocalKnowledgeRetriever(entries=(KnowledgeEntry(*entry),))

    results = await retriever.search("自定义")

    assert results == [("自定义知识内容", Citation("自定义", "kb://custom"))]


def test_load_entries_from_jsonl(tmp_path) -> None:
    path = tmp_path / "kb.jsonl"
    path.write_text(
        '{"content": "商品资料", "reference": "product://SG:1", '
        '"title": "商品资料", "keywords": ["耳机", "蓝牙"]}\n',
        encoding="utf-8",
    )

    entries = load_entries(path)

    assert len(entries) == 1
    assert entries[0].content == "商品资料"
    assert entries[0].citation.reference == "product://SG:1"
    assert entries[0].keywords == ("耳机", "蓝牙")


def test_load_entries_rejects_missing_fields(tmp_path) -> None:
    path = tmp_path / "kb.jsonl"
    path.write_text('{"content": "只有内容"}\n', encoding="utf-8")

    try:
        load_entries(path)
    except ValueError as error:
        assert "reference" in str(error)
    else:
        raise AssertionError("应当抛出 ValueError")
