from dataclasses import dataclass, field
from enum import StrEnum


class Intent(StrEnum):
    FAQ = "faq"
    PRODUCT = "product"
    ORDER = "order"
    AFTER_SALES = "after_sales"
    HUMAN_HANDOFF = "human_handoff"


@dataclass(frozen=True)
class Citation:
    title: str
    reference: str


@dataclass(frozen=True)
class SupportReply:
    answer: str
    intent: Intent
    citations: tuple[Citation, ...] = field(default_factory=tuple)
    requires_human: bool = False
    requires_confirmation: bool = False
