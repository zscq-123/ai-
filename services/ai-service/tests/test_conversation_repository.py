from contextlib import AbstractContextManager
from types import TracebackType
from typing import Any
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError

from ai_service.domain.models import Intent, SupportReply
from ai_service.infrastructure.conversation_repository import ConversationRecorder


class RecordingConnection:
    def __init__(self) -> None:
        self.statements: list[tuple[str, dict[str, Any]]] = []

    def execute(self, statement: object, parameters: dict[str, Any]) -> None:
        self.statements.append((str(statement), parameters))


class RecordingTransaction(AbstractContextManager[RecordingConnection]):
    def __init__(self, connection: RecordingConnection) -> None:
        self.connection = connection

    def __enter__(self) -> RecordingConnection:
        return self.connection

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


class RecordingEngine:
    def __init__(self) -> None:
        self.connection = RecordingConnection()

    def begin(self) -> RecordingTransaction:
        return RecordingTransaction(self.connection)


class FailingEngine:
    class FailingTransaction(AbstractContextManager[RecordingConnection]):
        def __enter__(self) -> RecordingConnection:
            raise SQLAlchemyError("database unavailable")

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: TracebackType | None,
        ) -> None:
            return None

    def begin(self) -> FailingTransaction:
        return self.FailingTransaction()


def recorder_with_engine(engine: object) -> ConversationRecorder:
    recorder = ConversationRecorder("postgresql+psycopg://unused", "deepseek-test", enabled=False)
    recorder._engine = engine  # type: ignore[assignment]
    return recorder


def conversation_parameters(engine: RecordingEngine) -> dict[str, Any]:
    statement, parameters = engine.connection.statements[0]
    assert "merchant_id" in statement
    return parameters


def test_records_resolved_conversation_for_merchant() -> None:
    engine = RecordingEngine()
    merchant_id = uuid4()
    recorder = recorder_with_engine(engine)

    recorder.record(
        "商品什么时候发货？",
        SupportReply("今天发货。", Intent.PRODUCT),
        21,
        merchant_id=merchant_id,
    )

    assert len(engine.connection.statements) == 3
    parameters = conversation_parameters(engine)
    assert parameters["merchant_id"] == merchant_id
    assert parameters["status"] == "RESOLVED"
    assert parameters["resolved_at"] is not None
    assert parameters["handed_off_at"] is None


def test_records_handoff_conversation_for_merchant() -> None:
    engine = RecordingEngine()
    merchant_id = uuid4()
    recorder = recorder_with_engine(engine)

    recorder.record(
        "我要转人工",
        SupportReply("正在转接。", Intent.HUMAN_HANDOFF, requires_human=True),
        9,
        merchant_id=merchant_id,
    )

    parameters = conversation_parameters(engine)
    assert parameters["merchant_id"] == merchant_id
    assert parameters["status"] == "HANDED_OFF"
    assert parameters["handed_off_at"] is not None
    assert parameters["resolved_at"] is None


def test_does_not_guess_merchant_for_legacy_request() -> None:
    engine = RecordingEngine()
    recorder = recorder_with_engine(engine)

    recorder.record(
        "商品什么时候发货？",
        SupportReply("今天发货。", Intent.PRODUCT),
        21,
        merchant_id=None,
    )

    assert engine.connection.statements == []


def test_disabled_recorder_keeps_tests_isolated_from_database() -> None:
    recorder = ConversationRecorder(
        "postgresql+psycopg://invalid-host/unused",
        "deepseek-test",
        enabled=False,
    )

    recorder.record(
        "商品什么时候发货？",
        SupportReply("今天发货。", Intent.PRODUCT),
        21,
        merchant_id=uuid4(),
    )


def test_database_failure_does_not_escape(caplog: Any) -> None:
    recorder = recorder_with_engine(FailingEngine())

    recorder.record(
        "商品什么时候发货？",
        SupportReply("今天发货。", Intent.PRODUCT),
        21,
        merchant_id=uuid4(),
    )

    assert "Unable to persist AI support conversation" in caplog.text
