import json
import logging
from datetime import UTC, datetime
from functools import lru_cache
from time import perf_counter
from uuid import UUID, uuid4

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from ai_service.domain.models import SupportReply

logger = logging.getLogger(__name__)


class ConversationRecorder:
    def __init__(self, database_url: str, model_name: str, *, enabled: bool = True) -> None:
        self._enabled = enabled
        self._model_name = model_name
        self._engine = _engine(database_url) if enabled else None

    def merchant_is_active(self, merchant_id: UUID) -> bool | None:
        """Return None when persistence is disabled or temporarily unavailable."""
        if self._engine is None:
            return None
        try:
            with self._engine.connect() as connection:
                return bool(
                    connection.execute(
                        text(
                            "select exists(select 1 from merchants "
                            "where id=:id and status='ACTIVE')"
                        ),
                        {"id": merchant_id},
                    ).scalar_one()
                )
        except SQLAlchemyError:
            logger.exception("Unable to validate AI support merchant")
            return None

    def record(
        self,
        question: str,
        reply: SupportReply,
        elapsed_ms: int,
        *,
        merchant_id: UUID | None,
    ) -> None:
        if self._engine is None or merchant_id is None:
            return
        conversation_id = uuid4()
        status = "HANDED_OFF" if reply.requires_human else "RESOLVED"
        completed_at = datetime.now(UTC)
        citations = json.dumps(
            [{"title": item.title, "reference": item.reference} for item in reply.citations],
            ensure_ascii=False,
        )
        try:
            with self._engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        insert into ai_conversations(
                            id,merchant_id,status,handed_off_at,resolved_at
                        ) values (
                            :id,:merchant_id,:status,:handed_off_at,:resolved_at
                        )
                        """
                    ),
                    {
                        "id": conversation_id,
                        "merchant_id": merchant_id,
                        "status": status,
                        "handed_off_at": completed_at if reply.requires_human else None,
                        "resolved_at": None if reply.requires_human else completed_at,
                    },
                )
                connection.execute(
                    text(
                        """
                        insert into ai_messages(id,conversation_id,role,content)
                        values (:id,:conversation_id,'user',:content)
                        """
                    ),
                    {"id": uuid4(), "conversation_id": conversation_id, "content": question},
                )
                connection.execute(
                    text(
                        """
                        insert into ai_messages(
                            id,conversation_id,role,content,intent,citations,model_name,latency_ms
                        ) values (
                            :id,:conversation_id,'assistant',:content,:intent,
                            cast(:citations as jsonb),:model_name,:latency_ms
                        )
                        """
                    ),
                    {
                        "id": uuid4(),
                        "conversation_id": conversation_id,
                        "content": reply.answer,
                        "intent": reply.intent.value,
                        "citations": citations,
                        "model_name": self._model_name,
                        "latency_ms": elapsed_ms,
                    },
                )
        except SQLAlchemyError:
            logger.exception("Unable to persist AI support conversation")


@lru_cache(maxsize=4)
def _engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True, connect_args={"connect_timeout": 2})


class ConversationTimer:
    def __init__(self) -> None:
        self._started = perf_counter()

    def elapsed_ms(self) -> int:
        return round((perf_counter() - self._started) * 1000)
