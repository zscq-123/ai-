"""把话术库导出为 Markdown 手册与 SFT 种子集。

用法（在 services/ai-service 目录）：
    PYTHONPATH=src ../../.venv/bin/python -m ai_service.prompts.export
"""

import json
from pathlib import Path

from ai_service.prompts.library import (
    EVIDENCE_RULES,
    GLOBAL_RULES,
    SCRIPT_CARDS,
    TONE_TABLE,
    ScriptCard,
)

_REPO_ROOT = Path(__file__).resolve().parents[5]
_MANUAL_PATH = _REPO_ROOT / "docs" / "话术手册.md"
_SEED_PATH = _REPO_ROOT / "services" / "ai-service" / "datasets" / "scripts_sft_seed.jsonl"

_ROLE_LINE = (
    "你是电商平台的在线客服小助手，负责商品、订单与售后咨询。"
    "只依据平台规则与用户提供的信息作答，不编造商品、订单、库存、价格与售后状态。"
)


def _card_section(card: ScriptCard) -> str:
    lines = [
        f"### {card.id} {card.title}",
        "",
        f"- **对应意图**：`{card.intent.value}`",
        f"- **需要知识库**：{'是' if card.needs_knowledge else '否'}",
        "- **处理步骤**：",
        *(f"  {index}. {step}" for index, step in enumerate(card.structure, start=1)),
        "",
        "**模板**",
        "",
        "```text",
        card.template,
        "```",
        "",
        "**范例**",
        "",
    ]
    for question, answer in card.examples:
        lines.extend(
            [
                f"> 用户：{question}",
                f"> 客服：{answer}",
                "",
            ]
        )
    if card.avoid:
        lines.append("**禁忌**")
        lines.append("")
        lines.extend(f"- {item}" for item in card.avoid)
        lines.append("")
    return "\n".join(lines)


def render_manual() -> str:
    parts = [
        "# 客服话术手册",
        "",
        "> 本文件由 `ai_service.prompts.library` 自动生成，请勿直接编辑。",
        "> 修改话术请改 `services/ai-service/src/ai_service/prompts/library.py` 后重新导出。",
        "",
        "## 一、总则",
        "",
        "### 1.1 角色",
        "",
        _ROLE_LINE,
        "",
        "### 1.2 真人客服的接话方式",
        "",
        "先回应用户当下的问题，用一到三句说清楚。问候、致谢可以只有一句；",
        "用户着急时先具体回应他的处境，缺信息时只问一个关键问题，答完就停。",
        "不要求每轮凑齐共情、结论、依据、下一步和收尾，也不用固定开场和服务菜单。",
        "",
        "以下范例是为项目编写的风格示例，并非真实客服聊天记录，也不代表已经完成模型微调。",
        "运行时将场景示例加入提示词，引导表达；业务事实仍以本轮知识与工具结果为准。",
        "",
        "### 1.3 事实与证据规则",
        "",
        *(f"{index}. {rule}" for index, rule in enumerate(EVIDENCE_RULES, start=1)),
        "",
        "### 1.4 表达规范",
        "",
        *(f"{index}. {rule}" for index, rule in enumerate(GLOBAL_RULES, start=1)),
        "",
        "### 1.5 语气对照",
        "",
        "| 不要这样说 | 改成这样说 |",
        "| --- | --- |",
        *(f"| {bad} | {good} |" for bad, good in TONE_TABLE),
        "",
        "## 二、场景话术卡",
        "",
        f"共 {len(SCRIPT_CARDS)} 张，按意图与关键词自动选择。",
        "",
    ]
    parts.extend(_card_section(card) for card in SCRIPT_CARDS)
    parts.extend(
        [
            "## 三、风控红线",
            "",
            "- 可以解释退款与售后规则；用户要求实际退款或涉及资金时，立即转人工核对。",
            "- 修改地址、取消未发货订单等操作，必须先完成身份校验，并在提交前让用户确认。",
            "- 未完成身份校验前，不得透露任何订单内容。",
            "- 用户要求人工，或提到投诉、律师、报警、重要订单、支付异常时，立即转人工。",
            "- 用户表示前面的回答没解决或答非所问时，停止重复原答案，转人工接手。",
            "- 不评价竞品，不透露成本、底价与内部系统字段。",
            "- 信息缺失时说清楚缺什么，并提供可行路径；没有执行结果，不声称已催件或已转接。",
            "- 自然表达不等于假冒人工；被问到身份时如实说明是 AI 客服。",
            "",
            "## 四、度量指标",
            "",
            "| 指标 | 定义 | 目标 |",
            "| --- | --- | --- |",
            "| 建议采纳率 | 座席采纳的建议条数 / 推送总条数 | ≥ 35% |",
            "| 首答准确率 | 人工抽检判定正确的首条回复占比 | ≥ 90% |",
            "| 违规率 | 出现承诺、编造、越权的回复占比 | ≤ 1% |",
            "| 转人工正确率 | 需要人工的高风险场景被正确标记的占比 | ≥ 95% |",
            "| 回复长度 | 简单回复一到三句；问候和致谢可以更短 | ≤ 120 字 |",
            "| 自然度 | 人工抽检是否接住问题、追问必要、没有模板感 | 人工评审 |",
            "",
            "## 五、维护方式",
            "",
            "1. 改话术：编辑 `library.py` 中的 `ScriptCard`，"
            "新增场景需在 `select_card` 登记触发词。",
            "2. 重新导出：`PYTHONPATH=src ../../.venv/bin/python -m ai_service.prompts.export`。",
            "3. 回归测试：`python -m pytest tests/test_prompt_composer.py`。",
            "4. 学习指定客服：使用有权使用且已脱敏的对话，保留用户问题和客服回复配对；"
            "按场景挑选自然、准确的范例，去掉个人信息、未经兑现的承诺和过期政策。",
            "5. 将审核后的表达范例加入对应卡片的 `examples`，重新导出即可用于提示词示范；"
            "示例不是本轮事实，不把历史订单金额或时限套用给其他用户。",
            "6. `datasets/scripts_sft_seed.jsonl` 是示范种子集，导出不等于模型已训练；"
            "若后续微调，应另留未参与训练的真实对话做准确性和自然度验收。",
            "",
        ]
    )
    return "\n".join(parts)


def render_seed_jsonl() -> str:
    """生成 SFT 种子集：system + user + assistant 三段式。"""

    rows: list[str] = []
    system = (
        _ROLE_LINE
        + "\n最高优先级：事实与证据规则：\n"
        + "\n".join(f"- {rule}" for rule in EVIDENCE_RULES)
        + "\n表达规范：\n"
        + "\n".join(f"- {rule}" for rule in GLOBAL_RULES)
    )
    for card in SCRIPT_CARDS:
        for question, answer in card.examples:
            rows.append(
                json.dumps(
                    {
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": question},
                            {"role": "assistant", "content": answer},
                        ],
                        "meta": {
                            "card_id": card.id,
                            "scenario": card.title,
                            "source": "authored_style_example",
                        },
                    },
                    ensure_ascii=False,
                )
            )
    return "\n".join(rows) + "\n"


def main() -> None:
    _MANUAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    _MANUAL_PATH.write_text(render_manual(), encoding="utf-8")

    _SEED_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SEED_PATH.write_text(render_seed_jsonl(), encoding="utf-8")

    print(f"manual: {_MANUAL_PATH}")
    print(f"seed:   {_SEED_PATH}")


if __name__ == "__main__":
    main()
