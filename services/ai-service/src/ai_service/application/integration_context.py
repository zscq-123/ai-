"""Bounded conversation hints, never cached business facts or model answers."""

import time
from collections import OrderedDict
from dataclasses import dataclass


@dataclass(frozen=True)
class ConversationHint:
    question: str
    topic: str | None


class IntegrationContextStore:
    def __init__(self, *, ttl: float = 1800, capacity: int = 1000):
        self.ttl = ttl
        self.capacity = capacity
        self._items: OrderedDict[tuple[str, str | None, str], tuple[float, ConversationHint]] = (
            OrderedDict()
        )

    def get(
        self, source: str, subject: str | None, conversation: str | None
    ) -> ConversationHint | None:
        if not conversation:
            return None
        key = (source, subject, conversation)
        item = self._items.get(key)
        if item is None:
            return None
        if time.monotonic() - item[0] >= self.ttl:
            del self._items[key]
            return None
        return item[1]

    def put(
        self, source: str, subject: str | None, conversation: str | None, hint: ConversationHint
    ) -> None:
        if not conversation:
            return
        key = (source, subject, conversation)
        self._items[key] = (time.monotonic(), hint)
        self._items.move_to_end(key)
        while len(self._items) > self.capacity:
            self._items.popitem(last=False)

    def clear(self) -> None:
        self._items.clear()
