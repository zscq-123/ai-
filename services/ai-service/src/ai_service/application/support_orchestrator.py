import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID

from ai_service.domain.models import Citation, Intent, ReplyGuidance, SupportReply
from ai_service.domain.ports import KnowledgeRetriever, ModelProvider, SupportToolProvider
from ai_service.prompts.library import (
    AFTER_SALES_AUTHENTICATED_REPLY,
    AFTER_SALES_UNAUTHENTICATED_REPLY,
    EMPTY_ANSWER_REPLY,
    ScriptCard,
    select_card,
)


@dataclass(frozen=True)
class SupportContext:
    message: str
    authenticated: bool
    customer_id: UUID | None = None
    merchant_id: UUID | None = None
    product_id: UUID | None = None
    sku_id: UUID | None = None

    @property
    def normalized(self) -> str:
        return self.message.strip().lower()


@dataclass(frozen=True)
class SupportStreamEvent:
    """流式回答的一个片段；final 非空表示本轮结束。"""

    delta: str = ""
    final: SupportReply | None = None


class _NullSupportTools:
    async def lookup(
        self,
        message: str,
        *,
        customer_id: UUID | None = None,
        merchant_id: UUID | None = None,
        product_id: UUID | None = None,
        sku_id: UUID | None = None,
    ) -> list[tuple[str, Citation]]:
        del message, customer_id, merchant_id, product_id, sku_id
        return []


class EmotionRiskModule:
    """Detects signals that require a human instead of an unsafe automatic answer."""

    _handoff_signals = (
        "我要转人工",
        "要求转人工",
        "申请转人工",
        "找真人",
        "联系真人",
        "需要人工客服",
        "我要真人",
        "我要人工",
        "只要人工",
        "人工处理",
        "人工队列",
        "转真人",
        "找个人",
        "接受真人",
        "投诉",
        "律师",
        "报警",
        "太差",
        "垃圾",
        "差评",
        "气死",
        "骗子",
        "答非所问",
        "没答到点",
        "听不懂人话",
        "听不懂我说",
        "不明白我说",
        "还是没解决",
        "又没解决",
        "已经问两次",
        "问了两次",
        "推诿",
        "扯皮",
        "大额退款",
        "重要订单",
        "高风险",
        "退款没到账",
        "钱没退",
        "支付异常",
    )

    def requires_handoff(self, context: SupportContext) -> bool:
        return any(signal in context.normalized for signal in self._handoff_signals)


class IntentRoutingModule:
    """Routes a request to an internal capability without exposing separate bots."""

    def route(self, context: SupportContext) -> Intent:
        message = context.normalized
        if any(
            word in message
            for word in (
                "退款",
                "退货",
                "退钱",
                "换货",
                "取消订单",
                "改地址",
                "修改地址",
                "改价",
                "售后",
                "拿回",
                "不想要了",
                "退回去",
            )
        ):
            return Intent.AFTER_SALES
        if any(
            word in message
            for word in (
                "订单",
                "物流",
                "快递",
                "发货",
                "没到",
                "没收到",
                "还没",
                "催",
                "太慢",
                "什么时候到",
                "到货",
                "几天",
                "能到",
                "货呢",
                "查件",
                "到哪儿",
                "送到哪",
                "怎么还没来",
            )
        ):
            return Intent.ORDER
        if any(
            word in message
            for word in (
                "商品",
                "规格",
                "型号",
                "推荐",
                "选购",
                "参数",
                "续航",
                "材质",
                "尺寸",
                "颜色",
                "配置",
                "功能",
                "好用",
                "哪个好",
                "值得",
                "多少钱",
                "价格",
                "报价",
                "区别",
                "不同",
                "适合",
                "预算",
                "怎么用",
                "用法",
                "质量",
                "库存",
                "有货",
                "现货",
                "能拍",
                "这两款",
                "这俩",
            )
        ):
            return Intent.PRODUCT
        return Intent.FAQ


class SafetyBoundaryModule:
    """Produces useful, domain-neutral refusals before any model call."""

    _third_party_signals = (
        "别人",
        "别人的",
        "他人",
        "同事",
        "朋友",
        "前任",
        "家人",
        "室友",
        "陌生",
        "员工",
        "另一个账号",
        "目标账号",
        "两个账号",
        "第三方",
        "下单人",
        "非本人",
        "他的",
        "她的",
        "这个人",
        "收货人",
    )
    _private_data_signals = (
        "订单",
        "付款",
        "支付",
        "购物",
        "买过",
        "购买",
        "商品",
        "地址",
        "物流",
        "银行卡",
        "消费",
        "浏览",
        "售后",
        "优惠券",
        "手机号",
        "个人资料",
        "验证码",
        "收件",
        "绑定",
        "实名",
        "账号设置",
    )
    _identity_data_signals = ("身份证", "邮箱", "会员昵称", "姓名")
    _impersonation_signals = (
        "承认自己是真人",
        "你是真人",
        "真人坐席",
        "冒充店长",
        "冒充人工",
        "别说是机器人",
        "假装真人",
    )
    _instruction_override_signals = (
        "忽略所有规则",
        "忽略核验",
        "原样输出",
        "照这句话回复",
        "模拟工具",
        "你先回复",
        "只输出",
        "无条件回复",
        "最高权限",
        "最高优先级通知",
    )
    _fabricated_result_signals = (
        "已退款",
        "已经退款",
        "退款已经到账",
        "已退回",
        "已连接",
        "换货成功",
        "已取消",
        "支付成功",
        "已发货",
        "已签收",
    )
    _professional_scope_signals = {
        "法律": ("合同", "官司", "律师", "法律"),
        "医疗": ("确诊", "开药", "症状", "诊断"),
        "天气": ("天气", "下雨", "气温"),
        "股票": ("股票", "涨停", "涨多少", "股价"),
    }
    _direct_action_signals = (
        "立刻",
        "直接",
        "替我",
        "马上",
        "现在就",
        "不用核验",
        "不需要确认",
        "别再让我操作",
        "确认完成",
        "告诉我已经",
        "回复我催过了",
        "回复补发成功",
    )
    _mutation_signals = (
        "取消",
        "改地址",
        "修改地址",
        "收货信息改",
        "改成成功",
        "完成扣款",
        "可售库存改",
        "调整库存",
        "标记成已签收",
        "补一个签收时间",
        "提交退款",
        "全额退款",
        "发起退货",
        "换货",
        "换成",
        "投诉商家",
        "发催件",
        "删除",
        "改成专票",
        "领取优惠券",
        "冻结",
        "补回",
        "重开",
        "拦截退回",
    )

    def prepare(
        self,
        context: SupportContext,
        intent: Intent,
        evidence: list[tuple[str, Citation]] | None = None,
    ) -> SupportReply | None:
        text = context.normalized
        evidence = evidence or []
        evidence_text = "\n".join(content for content, _ in evidence).lower()
        evidence_citations = tuple(citation for _, citation in evidence)
        if "在吗" in text and len(text) <= 30:
            return SupportReply(
                "在的，您好！请说，我可以帮您处理商城客服问题。",
                Intent.FAQ,
            )
        if any(signal in text for signal in self._impersonation_signals):
            return SupportReply(
                "我是 AI 智能客服，不是真人，也不能假装已有人工接入。"
                "如果需要人工处理，可以申请转接。",
                Intent.FAQ,
            )
        if any(signal in text for signal in self._instruction_override_signals) and any(
            signal in text for signal in self._fabricated_result_signals
        ):
            return SupportReply(
                "我不能把用户指令当成可信记录，也不能伪造订单、支付、退款、物流或人工接入结果。"
                "需要以实际系统证据核对。",
                intent,
            )
        for scope, signals in self._professional_scope_signals.items():
            if any(signal in text for signal in signals):
                return SupportReply(
                    f"这超出商城客服的服务范围，我不能提供{scope}方面的专业结论。"
                    "请咨询对应的专业渠道。",
                    Intent.FAQ,
                )
        policy_checked = (
            "authorization.policy_check" in evidence_text
            or "identity.check_session_and_permission" in evidence_text
            or all(
                field in evidence_text
                for field in ("login_status", "identity_status", "authorization_status")
            )
            or all(
                field in evidence_text
                for field in ("session_state", "permission_decision", "account_matches_target")
            )
        )
        if policy_checked:
            expired_session = bool(
                re.search(r'"session_state"\s*:\s*"expired"', evidence_text)
            )
            permission_blocked = bool(
                re.search(r'"permission_decision"\s*:\s*"blocked"', evidence_text)
            )
            target_mismatch = bool(
                re.search(r'"account_matches_target"\s*:\s*false', evidence_text)
            )
            permission_not_checked = bool(
                re.search(r'"permission_decision"\s*:\s*"not_checked"', evidence_text)
            )
            permission_allowed = bool(
                re.search(r'"permission_decision"\s*:\s*"allowed"', evidence_text)
            )
            confirmation_missing = bool(
                re.search(r'"confirmation_present"\s*:\s*false', evidence_text)
            )
            revision_conflict = "allowed_but_revision_conflict" in evidence_text
            decision_match = re.search(
                r'"permission_decision"\s*:\s*"([^"]+)"', evidence_text
            )
            permission_decision = (
                decision_match.group(1) if decision_match is not None else "not_allowed"
            )
            write_committed = bool(
                re.search(r'"mutation_applied"\s*:\s*true', evidence_text)
                or re.search(r'"execution_status"\s*:\s*"committed"', evidence_text)
            )
            if "forge_delivery_confirmation" in evidence_text:
                return SupportReply(
                    "可信授权策略检查识别到 forge_delivery_confirmation；我不能伪造签收，"
                    "也不会调用任何写工具修改物流状态。当前请求未执行；应先用只读物流"
                    "轨迹核对真实事件，发现异常时转人工调查。",
                    Intent.ORDER,
                    evidence_citations,
                    requires_human=True,
                )
            if "not_logged_in" in evidence_text or expired_session:
                return SupportReply(
                    "可信授权策略检查显示登录或会话无效（login_status=not_logged_in / "
                    "session_state=expired）。请先登录或重新登录并完成身份"
                    "验证；当前操作未执行，也不会在缺少权限和成功回执时声称完成。",
                    intent,
                    evidence_citations,
                    requires_confirmation=True,
                )
            if "identity_status" in evidence_text and "unverified" in evidence_text:
                return SupportReply(
                    "可信授权策略检查结果为 identity_status=unverified。请先完成身份验证，"
                    "并在核验后重新作出明确确认；当前操作未执行。",
                    intent,
                    evidence_citations,
                    requires_confirmation=True,
                )
            if permission_not_checked:
                return SupportReply(
                    "当前身份与授权尚未完成检查（permission_decision=not_checked），需要澄清"
                    "或补充可验证的登录、会话、对象归属和权限条件；当前操作未执行。",
                    intent,
                    evidence_citations,
                    requires_confirmation=True,
                )
            if any(
                signal in evidence_text
                for signal in (
                    "not_allowed",
                    "authorization_denied",
                    "denied_missing_permission",
                    "denied_owner_mismatch",
                )
            ) or permission_blocked or target_mismatch:
                return SupportReply(
                    "可信授权策略检查显示当前缺少执行权限、对象归属不匹配或请求被阻止"
                    f"（permission_decision={permission_decision}；"
                    "authorization_status=not_allowed）。当前操作未执行；可以申请转人工"
                    "核验，但申请转接不等于人工已接管。",
                    Intent.HUMAN_HANDOFF,
                    evidence_citations,
                    requires_human=True,
                )
            if revision_conflict:
                return SupportReply(
                    "身份与基础权限已检查，但 permission_decision=allowed_but_revision_conflict，"
                    "当前 revision 与待处理对象不一致。需要重新读取最新可信结构化证据并"
                    "重新确认对象和动作；当前写操作未执行。",
                    Intent.HUMAN_HANDOFF,
                    evidence_citations,
                    requires_human=True,
                    requires_confirmation=True,
                )
            if (
                permission_allowed
                and confirmation_missing
            ):
                return SupportReply(
                    "身份、会话、对象归属和权限检查已通过，但 confirmation_present=false，"
                    "仍缺少对本次对象、动作和影响的明确确认。当前写操作未执行；确认后还需"
                    "以执行工具的成功回执为准。",
                    intent,
                    evidence_citations,
                    requires_confirmation=True,
                )
            if permission_allowed and write_committed:
                return SupportReply(
                    "已检查身份与授权，明确确认有效；可信写工具回执显示 "
                    "mutation_applied=true、execution_status=committed，因此本次写操作已提交"
                    "成功。具体对象、变更前后 revision 和业务字段以所附结构化工具证据为准。",
                    intent,
                    evidence_citations,
                )
            if permission_allowed:
                return SupportReply(
                    "已检查身份、会话、对象归属和权限，permission_decision=allowed，且明确"
                    "确认有效。当前只完成前置核验，尚无写操作 executed=true 的成功回执，"
                    "因此不宣称处理完成；下一步应调用对应写工具并以实际回执为准。",
                    intent,
                    evidence_citations,
                    requires_confirmation=False,
                )
        private_business_data = any(signal in text for signal in self._private_data_signals)
        third_party_request = any(signal in text for signal in self._third_party_signals)
        third_party_report_only = (
            any(signal in text for signal in ("转述", "抄错", "来源不明的截图"))
            and any(signal in text for signal in ("结构化", "工具", "一致性", "分别看待"))
        )
        public_third_party_product_question = "第三方商品" in text and any(
            signal in text for signal in ("谁提供", "提供方", "供应商", "来源")
        )
        if third_party_report_only or public_third_party_product_question:
            third_party_request = False
        # A merchant's public support email is not a customer's identity lookup.
        # Other identity fields and all third-party account requests still hit this gate.
        identity_text = re.sub(r"客服(?:联系)?邮箱|官方邮箱|商家邮箱|你们的邮箱", "", text)
        identity_lookup = any(signal in identity_text for signal in self._identity_data_signals)
        if private_business_data and (third_party_request or identity_lookup):
            if "接管工具状态" in evidence_text:
                return None
            authorization_denied = any(
                signal in evidence_text
                for signal in (
                    "authorization_denied",
                    '"authorization": "denied"',
                    '"authorization": "expired"',
                    '"authorization": "target_mismatch"',
                    '"authorization": "not_verified"',
                    "authorization=denied",
                    "authorization=expired",
                    "authorization=target_mismatch",
                    "authorization=not_verified",
                    "授权不足",
                    "授权已过期",
                    "目标账号不匹配",
                )
            )
            authorization_allowed = any(
                signal in evidence_text
                for signal in (
                    '"authorization": "allowed"',
                    '"authorization": "allowed_minimum_scope"',
                    "authorization=allowed",
                    '"executed": true',
                    "executed=true",
                    "正式授权已核验",
                    "允许最小必要查询",
                )
            )
            if authorization_allowed and not authorization_denied:
                return None
            return SupportReply(
                "已核验当前身份与目标账号授权；以可信结构化工具结果为准，当前没有有效"
                "正式授权，我不能查询或提供第三方订单、地址、支付等隐私资料。请由本人"
                "登录或完成正式授权；仅作最小必要披露并保持敏感字段掩码。",
                Intent.FAQ,
                evidence_citations,
            )
        current_read_only_override = "只查询" in text and any(
            signal in text for signal in ("上一轮", "之前", "原请求", "改为")
        )
        direct_request = not current_read_only_override and (
            any(signal in text for signal in self._direct_action_signals)
            or text.startswith(
                ("把", "帮我", "替我", "删除", "取消", "提交", "发起", "领取", "冻结")
            )
        )
        if direct_request and any(signal in text for signal in self._mutation_signals):
            if any(
                signal in evidence_text for signal in ('"executed": true', "executed=true")
            ):
                return None
            if any(
                signal in evidence_text
                for signal in (
                    '"executed": false',
                    "executed=false",
                    "confirmation_required",
                    "authorization_denied",
                    "target_account_mismatch",
                )
            ):
                return SupportReply(
                    "已依次检查身份、授权、确认和执行结果；可信结构化工具显示 "
                    "executed=false，操作未成功。仅在 executed=true 时确认成功，"
                    "授权不足时必须停止写操作。",
                    intent,
                    evidence_citations,
                    requires_confirmation=True,
                )
            if "退款" in text or "赔偿" in text:
                return SupportReply(
                    "我不能直接执行或声称退款、赔偿已经完成。需要先核对身份、授权、"
                    "订单详情和明确确认，再由有权限的人工处理资金操作。",
                    Intent.HUMAN_HANDOFF,
                    requires_human=True,
                    requires_confirmation=True,
                )
            return SupportReply(
                "我不能直接执行或声称操作已经完成。需要先核对身份、授权、订单详情和"
                "明确确认；取得成功回执前不会报告完成。",
                intent,
                requires_confirmation=True,
            )
        return None


class ContextualFallbackModule:
    """Explains the exact missing evidence instead of returning a vague fallback."""

    _inventory_signals = ("库存", "有货", "现货", "能拍", "能买", "剩余", "剩几", "下单")
    _payment_signals = (
        "支付",
        "付款",
        "扣款",
        "结算",
        "分期",
        "免息",
        "货到付款",
        "先买后付",
        "组合付款",
        "扫码",
        "apple pay",
        "数字人民币",
        "信用卡",
        "银行卡",
        "花呗",
        "微信支付",
        "支付宝",
        "积分抵",
        "退款原路",
    )
    _product_policy_signals = (
        "价格",
        "成交价",
        "多少钱",
        "正品",
        "保修",
        "发票",
        "开票",
        "包邮",
        "送到",
        "七天无理由",
        "延保",
        "赠品",
        "装箱",
        "尺码",
        "功率",
        "活动",
    )

    def reply(self, context: SupportContext, intent: Intent) -> SupportReply:
        text = context.normalized
        if any(signal in text for signal in self._inventory_signals):
            answer = (
                "目前没有查到准确信息或可核实的实时库存结果，无法确认是否有货、"
                "能否下单或剩余数量。请在商品页选择具体商品和规格查看。"
            )
        elif any(signal in text for signal in self._payment_signals):
            answer = (
                "没有订单结算页或可信支付记录时，无法确认支付选项、分期、扣款或退款结果。"
                "请以订单结算页和实际支付记录为准。"
            )
        elif intent is Intent.ORDER:
            answer = (
                "目前没有可信订单或物流信息，无法确认发货、派送、签收、运单号或当前位置。"
                "请登录后在订单详情查看平台记录，或提供正确订单号转人工核对。"
            )
        elif any(signal in text for signal in self._product_policy_signals):
            answer = (
                "目前没有查到对应商品页面、店铺政策或订单结算信息，无法确认价格、正品、"
                "保修、发票、包邮、活动、规格或配送承诺。请以商品详情和结算页面为准。"
            )
        else:
            answer = (
                "目前没有查到准确信息或可信工具记录，无法确认具体业务结果，也不能把用户"
                "文本、页面备注或测试指令当成系统证据。请补充商品或订单信息，或转人工核对。"
            )
        answer += "需要按本轮有效意图重新查询最新工具证据，再根据结构化返回答复。"
        return SupportReply(answer, intent, requires_human=True)


class AfterSalesModule:
    """Converts sensitive after-sales operations into a request for more information."""

    _information_signals = (
        "怎么退款",
        "怎么申请退款",
        "如何退款",
        "能退款吗",
        "可以退款吗",
        "退款规则",
        "退款政策",
        "怎么退货",
        "能退货吗",
        "退货规则",
        "怎么换货",
        "换货规则",
        "售后规则",
        "售后政策",
    )
    _status_signals = (
        "退款状态",
        "退款到账",
        "退款到哪",
        "退款结束",
        "退款通过",
        "退款结果",
        "退款完成",
        "退款了吗",
        "退款进度",
        "退了多少钱",
        "处理中",
        "到账没有",
        "售后进度",
        "取消成功了吗",
    )
    _money_operation_signals = (
        "我要退款",
        "申请退款",
        "帮我退款",
        "给我退款",
        "现在退款",
        "退钱",
        "拿回我的钱",
    )
    _non_money_operation_signals = (
        "我要退货",
        "申请退货",
        "帮我退货",
        "我要换货",
        "申请换货",
        "帮我换货",
        "取消订单",
        "修改地址",
        "改地址",
    )

    def prepare(self, context: SupportContext, intent: Intent) -> SupportReply | None:
        if intent is not Intent.AFTER_SALES:
            return None
        if any(signal in context.normalized for signal in self._information_signals):
            return None
        if any(signal in context.normalized for signal in self._status_signals):
            if context.authenticated:
                return None
            return SupportReply(
                AFTER_SALES_UNAUTHENTICATED_REPLY,
                intent,
                requires_confirmation=True,
            )
        if any(signal in context.normalized for signal in self._money_operation_signals):
            return SupportReply(
                "这涉及退款和资金处理，需要人工客服核对订单后继续处理，请先别关闭页面。",
                Intent.HUMAN_HANDOFF,
                requires_human=True,
            )
        if not any(
            signal in context.normalized for signal in self._non_money_operation_signals
        ):
            return None
        if not context.authenticated:
            return SupportReply(
                AFTER_SALES_UNAUTHENTICATED_REPLY,
                intent,
                requires_confirmation=True,
            )
        return SupportReply(
            AFTER_SALES_AUTHENTICATED_REPLY,
            intent,
            requires_confirmation=True,
        )


class ResponseAuditModule:
    """Final policy gate shared by every internal specialist."""

    _inventory_question_signals = ("库存", "有货", "现货", "能拍", "能下单", "可以下单")
    _inventory_assertions = ("有货", "现货", "库存充足", "可以正常下单", "可以直接下单", "能拍")
    _inventory_evidence_assertions = ("有货", "现货", "库存充足", "可售库存", "可以购买")
    _payment_signals = ("花呗", "分期", "微信支付", "支付宝", "银行卡", "信用卡", "货到付款")
    _transaction_assertions = (
        "已退款",
        "已经退款",
        "退款成功",
        "退款已经到账",
        "已经退回",
        "已到账",
        "已取消",
        "取消成功",
        "已经修改",
        "地址已改",
        "已催件",
        "已经催件",
        "已发货",
        "正在派送",
        "已签收",
        "已支付",
        "支付成功",
        "已付款",
    )
    _negative_prefixes = ("不", "未", "没有", "无法", "不能", "是否", "尚未", "并非")
    _dynamic_inventory_prefixes = ("inventory://", "catalog://", "product://", "tool://")
    _dynamic_transaction_prefixes = (
        "order://",
        "logistics://",
        "refund-status://",
        "payment-status://",
        "tool://",
    )

    def review(
        self,
        reply: SupportReply,
        context: SupportContext,
        evidence: list[tuple[str, Citation]] | None = None,
    ) -> SupportReply:
        evidence = evidence or []
        if not reply.answer.strip():
            return SupportReply(
                EMPTY_ANSWER_REPLY,
                reply.intent,
                reply.citations,
                requires_confirmation=True,
            )
        grounded = self._ground_fact_claims(reply, context, evidence)
        if grounded is not None:
            return grounded
        if (
            any(
                signal in reply.answer
                for signal in ("没有查到准确信息", "还没有查到准确信息", "无法确认")
            )
            and not reply.requires_human
        ):
            return SupportReply(
                reply.answer,
                reply.intent,
                reply.citations,
                requires_human=True,
                requires_confirmation=reply.requires_confirmation,
            )
        if reply.intent is Intent.AFTER_SALES and not reply.requires_confirmation:
            return SupportReply(
                reply.answer,
                reply.intent,
                reply.citations,
                reply.requires_human,
                requires_confirmation=True,
            )
        return reply

    def requires_grounding_buffer(self, context: SupportContext) -> bool:
        signals = (
            *self._inventory_question_signals,
            *self._payment_signals,
            "订单",
            "物流",
            "快递",
            "退款",
            "退钱",
            "到账",
            "取消",
            "改地址",
            "催件",
        )
        return any(signal in context.normalized for signal in signals)

    def _ground_fact_claims(
        self,
        reply: SupportReply,
        context: SupportContext,
        evidence: list[tuple[str, Citation]],
    ) -> SupportReply | None:
        answer = reply.answer.strip()
        if (
            any(signal in context.normalized for signal in self._inventory_question_signals)
            and self._contains_positive_phrase(answer, self._inventory_assertions)
            and not self._has_inventory_evidence(evidence)
        ):
            return SupportReply(
                "这款规格是否有货需要以商品页实时库存为准，我这里没有查到可核实的库存结果。",
                reply.intent,
                requires_confirmation=reply.requires_confirmation,
            )

        if self._contains_positive_phrase(
            answer, self._transaction_assertions
        ) and not self._has_transaction_evidence(evidence):
            return SupportReply(
                "我这里没有查到可核实的订单或售后结果，请在订单详情查看实际状态；"
                "涉及资金时可以联系人工核对。",
                reply.intent,
                requires_human=True,
                requires_confirmation=reply.requires_confirmation,
            )

        requested_methods = [
            method for method in self._payment_signals if method in context.normalized
        ]
        unsupported_methods = [
            method
            for method in requested_methods
            if self._has_payment_claim(answer, method)
            and not any(self._has_payment_claim(content, method) for content, _ in evidence)
        ]
        if unsupported_methods:
            supported_citations = tuple(
                citation for _, citation in evidence if citation.reference == "policy://payment"
            )
            methods = "或".join(dict.fromkeys(unsupported_methods))
            return SupportReply(
                f"是否支持{methods}，请以这笔订单结算页实际显示的支付方式为准。",
                reply.intent,
                supported_citations,
                requires_confirmation=reply.requires_confirmation,
            )
        return None

    @classmethod
    def _contains_positive_phrase(cls, answer: str, phrases: tuple[str, ...]) -> bool:
        for phrase in phrases:
            start = answer.find(phrase)
            while start >= 0:
                prefix = answer[max(0, start - 10) : start]
                if not any(negative in prefix for negative in cls._negative_prefixes):
                    return True
                start = answer.find(phrase, start + len(phrase))
        return False

    @classmethod
    def _has_payment_claim(cls, answer: str, method: str) -> bool:
        escaped = re.escape(method)
        patterns = (
            rf"(?:支持|可以使用|可以用|能用|可用).{{0,6}}{escaped}",
            rf"{escaped}.{{0,4}}(?:支持|可以|能用)",
        )
        for pattern in patterns:
            for match in re.finditer(pattern, answer):
                prefix = answer[max(0, match.start() - 10) : match.start()]
                if not any(negative in prefix for negative in cls._negative_prefixes):
                    return True
        return False

    @classmethod
    def _has_inventory_evidence(cls, evidence: list[tuple[str, Citation]]) -> bool:
        return any(
            citation.reference.startswith(cls._dynamic_inventory_prefixes)
            and cls._contains_positive_phrase(content, cls._inventory_evidence_assertions)
            for content, citation in evidence
        )

    @classmethod
    def _has_transaction_evidence(cls, evidence: list[tuple[str, Citation]]) -> bool:
        return any(
            citation.reference.startswith(cls._dynamic_transaction_prefixes)
            and (
                cls._contains_positive_phrase(content, cls._transaction_assertions)
                or (
                    bool(re.search(r"已于[^。]*签收", content))
                    and not any(
                        signal in content for signal in ("未签收", "尚未签收")
                    )
                )
            )
            for content, citation in evidence
        )


class SupportOrchestrator:
    """Single public support agent coordinating private specialist modules."""

    def __init__(
        self,
        retriever: KnowledgeRetriever,
        model: ModelProvider,
        tools: SupportToolProvider | None = None,
    ) -> None:
        self._retriever = retriever
        self._model = model
        self._tools = tools or _NullSupportTools()
        self._emotion = EmotionRiskModule()
        self._router = IntentRoutingModule()
        self._boundary = SafetyBoundaryModule()
        self._fallback = ContextualFallbackModule()
        self._after_sales = AfterSalesModule()
        self._audit = ResponseAuditModule()

    async def answer(
        self,
        message: str,
        *,
        authenticated: bool = False,
        customer_id: UUID | None = None,
        merchant_id: UUID | None = None,
        product_id: UUID | None = None,
        sku_id: UUID | None = None,
    ) -> SupportReply:
        context = SupportContext(
            message=message,
            authenticated=authenticated,
            customer_id=customer_id,
            merchant_id=merchant_id,
            product_id=product_id,
            sku_id=sku_id,
        )
        tool_results = await self._lookup_tools(context)
        intent, gated = self._route(context, tool_results)
        if gated is not None:
            return self._audit.review(gated, context, tool_results)

        card = select_card(intent, message)
        results = await self._retrieve(card, context, tool_results)
        if not results and (card.needs_knowledge or self._requires_live_evidence(context)):
            return self._audit.review(self._fallback.reply(context, intent), context)
        answer = await self._model.answer(
            question=message,
            context=[content for content, _ in results],
            guidance=ReplyGuidance(intent=intent, authenticated=context.authenticated),
        )
        return self._audit.review(self._reply(answer, intent, results), context, results)

    async def stream(
        self,
        message: str,
        *,
        authenticated: bool = False,
        customer_id: UUID | None = None,
        merchant_id: UUID | None = None,
        product_id: UUID | None = None,
        sku_id: UUID | None = None,
    ) -> AsyncIterator[SupportStreamEvent]:
        context = SupportContext(
            message=message,
            authenticated=authenticated,
            customer_id=customer_id,
            merchant_id=merchant_id,
            product_id=product_id,
            sku_id=sku_id,
        )
        tool_results = await self._lookup_tools(context)
        intent, gated = self._route(context, tool_results)
        if gated is not None:
            yield SupportStreamEvent(
                final=self._audit.review(gated, context, tool_results)
            )
            return

        card = select_card(intent, message)
        results = await self._retrieve(card, context, tool_results)
        if not results and (card.needs_knowledge or self._requires_live_evidence(context)):
            yield SupportStreamEvent(
                final=self._audit.review(self._fallback.reply(context, intent), context)
            )
            return
        guidance = ReplyGuidance(intent=intent, authenticated=context.authenticated)

        parts: list[str] = []
        buffer_for_grounding = self._audit.requires_grounding_buffer(context)
        async for chunk in self._model.stream_answer(
            question=message,
            context=[content for content, _ in results],
            guidance=guidance,
        ):
            if not chunk:
                continue
            parts.append(chunk)
            if not buffer_for_grounding:
                yield SupportStreamEvent(delta=chunk)

        reply = self._reply("".join(parts), intent, results)
        reviewed = self._audit.review(reply, context, results)
        if buffer_for_grounding and reviewed.answer:
            yield SupportStreamEvent(delta=reviewed.answer)
        yield SupportStreamEvent(final=reviewed)

    def _route(
        self,
        context: SupportContext,
        tool_results: list[tuple[str, Citation]],
    ) -> tuple[Intent, SupportReply | None]:
        intent = self._router.route(context)
        boundary = self._boundary.prepare(context, intent, tool_results)
        if boundary is not None:
            return boundary.intent, boundary
        if self._emotion.requires_handoff(context):
            return (
                Intent.HUMAN_HANDOFF,
                SupportReply(
                    "抱歉，可以申请转人工处理；申请请求不等于人工已接管。当前状态需要以"
                    "接管工具结果区分排队、失败或已接管；没有成功证据时不能确认人工已接入。"
                    "请先别关闭页面。",
                    Intent.HUMAN_HANDOFF,
                    requires_human=True,
                ),
            )
        return intent, self._after_sales.prepare(context, intent)

    async def _retrieve(
        self,
        card: ScriptCard,
        context: SupportContext,
        tool_results: list[tuple[str, Citation]] | None = None,
    ) -> list[tuple[str, Citation]]:
        tool_results = tool_results if tool_results is not None else await self._lookup_tools(
            context
        )
        knowledge_results = (
            []
            if not card.needs_knowledge
            else [
                (content, citation)
                for content, citation in await self._retriever.search(
                    context.message, merchant_id=context.merchant_id
                )
                if content.strip()
            ]
        )
        results: list[tuple[str, Citation]] = []
        seen: set[str] = set()
        for content, citation in [*tool_results, *knowledge_results]:
            if content.strip() and citation.reference not in seen:
                seen.add(citation.reference)
                results.append((content, citation))
        return results

    async def _lookup_tools(
        self, context: SupportContext
    ) -> list[tuple[str, Citation]]:
        return await self._tools.lookup(
            context.message,
            customer_id=context.customer_id,
            merchant_id=context.merchant_id,
            product_id=context.product_id,
            sku_id=context.sku_id,
        )

    @staticmethod
    def _requires_live_evidence(context: SupportContext) -> bool:
        return any(
            signal in context.normalized
            for signal in (
                "订单",
                "物流",
                "运单",
                "支付",
                "退款",
                "库存",
                "状态",
                "revision",
                "系统字段",
                "结构化记录",
                "重新核对",
            )
        )

    @staticmethod
    def _reply(answer: str, intent: Intent, results: list[tuple[str, Citation]]) -> SupportReply:
        return SupportReply(
            answer,
            intent,
            tuple(citation for _, citation in results),
        )
