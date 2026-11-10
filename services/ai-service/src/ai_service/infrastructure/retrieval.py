"""按配置组装知识检索实现。"""

import logging
from pathlib import Path

from ai_service.config import Settings
from ai_service.domain.ports import KnowledgeRetriever
from ai_service.infrastructure.embeddings import LazyFastEmbedEmbedder
from ai_service.infrastructure.hybrid_knowledge import HybridKnowledgeRetriever
from ai_service.infrastructure.intent_knowledge import IntentExampleKnowledgeRetriever
from ai_service.infrastructure.local_knowledge import (
    DEFAULT_ENTRIES,
    KnowledgeEntry,
    LocalKnowledgeRetriever,
    load_entries,
)
from ai_service.infrastructure.remote_faq_knowledge import RemoteFaqKnowledgeRetriever
from ai_service.infrastructure.semantic_scope import SemanticScopeGuard
from ai_service.infrastructure.vector_knowledge import VectorKnowledgeRetriever

logger = logging.getLogger(__name__)


def build_knowledge_retriever(settings: Settings) -> KnowledgeRetriever:
    entries = DEFAULT_ENTRIES
    extra: tuple[KnowledgeEntry, ...] = ()
    if settings.knowledge_file:
        extra = load_entries(Path(settings.knowledge_file))
        logger.info("加载外部知识 %d 条：%s", len(extra), settings.knowledge_file)
        entries = entries + extra

    if settings.retriever.strip().lower() == "keyword":
        keyword = LocalKnowledgeRetriever(entries)
        logger.info("使用关键词检索")
        local: KnowledgeRetriever = keyword
    else:
        keyword = LocalKnowledgeRetriever(entries, allow_bigram_fallback=False)
        logger.info("使用向量 + 关键词融合检索：%s", settings.embedding_model)
        cache_dir = str(Path(settings.embedding_cache_dir).expanduser())
        embedder = LazyFastEmbedEmbedder(
            settings.embedding_model,
            cache_dir=cache_dir,
            local_files_only=settings.embedding_local_only,
        )
        vector = VectorKnowledgeRetriever(
            entries=entries,
            embedder=embedder,
            min_score=settings.embedding_min_score,
            fallback=None,
        )
        # 精确关键词命中略高于单路语义近邻，防止短口语被向量误排；
        # 向量仍负责补足关键词未命中的改写问法。
        base_local = SemanticScopeGuard(
            HybridKnowledgeRetriever(
                vector,
                keyword,
                primary_weight=1.2,
            ),
            embedder,
            supported_texts=[text for entry in entries for text in entry.embedding_texts],
        )
        extra_local: KnowledgeRetriever | None = None
        if extra:
            extra_keyword = LocalKnowledgeRetriever(extra, allow_bigram_fallback=False)
            extra_local = HybridKnowledgeRetriever(
                VectorKnowledgeRetriever(
                    embedder=embedder,
                    entries=extra,
                    min_score=settings.embedding_min_score,
                    fallback=None,
                ),
                extra_keyword,
                primary_weight=1.2,
            )
        local = IntentExampleKnowledgeRetriever(
            embedder,
            fallback=base_local,
            out_of_scope_fallback=extra_local,
        )

    enterprise_faq = RemoteFaqKnowledgeRetriever(
        settings.commerce_api_url,
        settings.trusted_context_secret,
    )
    return HybridKnowledgeRetriever(
        enterprise_faq,
        local,
        primary_weight=1.1,
    )
