"""客服话术体系：结构化的场景话术卡与表达规范。"""

from ai_service.prompts.composer import ComposedPrompt, compose_prompt
from ai_service.prompts.library import (
    AFTER_SALES_AUTHENTICATED_REPLY,
    AFTER_SALES_UNAUTHENTICATED_REPLY,
    EMPTY_ANSWER_REPLY,
    GLOBAL_RULES,
    HANDOFF_REPLY,
    SCRIPT_CARDS,
    TONE_TABLE,
    ScriptCard,
    render_template,
    select_card,
)

__all__ = [
    "AFTER_SALES_AUTHENTICATED_REPLY",
    "AFTER_SALES_UNAUTHENTICATED_REPLY",
    "ComposedPrompt",
    "EMPTY_ANSWER_REPLY",
    "GLOBAL_RULES",
    "HANDOFF_REPLY",
    "SCRIPT_CARDS",
    "TONE_TABLE",
    "ScriptCard",
    "compose_prompt",
    "render_template",
    "select_card",
]
