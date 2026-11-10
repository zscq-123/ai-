# 154.36.185.110 商品购买链接与 Flash 客服部署

部署时间：2026-11-10（北京时间）。服务器：`154.36.185.110`，发布目录 `/opt/support-suite/current`。
本次只更新独立站相关服务，未迁移数据库、未修改 OMS。

## 更新内容

| 组件 | 服务器位置 | 内容 |
| --- | --- | --- |
| 独立站后端 | `jars/buzud-api.jar` | 商品目录证据、按需求反推、商品购买链接 `products`、聊天响应扩展 |
| AI 客服 | `ai-src-agents-20261106/ai_service` | `deepseek-flash` 关闭思考模式、800 token、商品上下文兜底、商品查询绕过多 Agent、聊天提示词要求商品链接 |
| 独立站前端 | `web-app/.next`、`web-app/server.js` | 商品购买卡片「去购买」、聊天记录 `sessionStorage` 保持 |

AI 实际挂载目录是 `ai-src-agents-20261106`，不是 `ai-src`。首次重启因只更新了 `ai-src`，AI 返回 422；随后同步到实际挂载目录并重启，恢复正常。

## 备份与回退

- 完整备份：`/opt/support-suite/backups/20261110-product-links`（约 63 MB）
  - 旧 `jars/buzud-api.jar`
  - 旧 `ai-src/ai_service`
  - 旧 `web-app/.next`、`web-app/server.js`
  - 旧 `compose.json`
- AI 实际源码备份：`/opt/support-suite/current/ai-src-agents-20261106.backup-20261110`
- 回退：恢复上述文件后，执行
  ```sh
  cd /opt/support-suite/current
  docker compose -f compose.json up -d --no-deps --force-recreate buzud-api support-ai buzud-web
  ```

## 验证结果

- 12 个容器全部 Up；`buzud-api`、`support-ai`、`buzud-web` 已按新代码重建/重启。
- 公网站点：`https://154.36.185.110:18083/zh/`、`/zh/all-products/`、商品详情页均 200；OMS `/support` 200。
- 公网客服接口：`POST /api/v1/chat/messages` 返回 200，预算血压计问题返回 6 个 `products`（30S、30C、30M、C02、U82RH、630CR），含名称、价格、图片和 `/zh/p/.../` 购买链接。
- 公网浏览器（Chrome）：商品卡片正常渲染，「去购买」指向对应商品页；发送消息后跳转 `/zh/all-products/`，聊天记录仍在（user=1、bot=2）。
- AI 日志：修复后 `POST /v1/integrations/buzud/chat` 返回 200；`buzud-api`、`buzud-web` 无 ERROR。
- 本地验证：独立站后端 232 项测试通过（9 项数据库测试跳过）；AI 235 项通过，mypy/ruff 通过；前端 tsc/eslint/prettier 通过。
- 数据库：Flyway 26 个迁移已是最新，无需迁移。
- 资源：内存可用约 1 GB，Swap 约 1.3 GB 已用；磁盘可用约 4.3 GB。

## 当前边界

- `BUZUD_OMS_ENABLED=false`，商品卡片和客服回答中的库存仍提示“以商品页和结算结果为准”，不提供实时可售数量。启用 OMS 并建立 `oms_sku_mapping` 后才会返回实时库存。
- 本次未启用真实支付、物流下单或邮件发送；这些配置未改动。
- 优惠券工具仍未接入商品问答。

## 追加更新：问候与闲聊

2026-11-10 晚追加部署 AI 客服的社交消息处理：

- 能识别 `ciallo`、`Ciallo～(∠・ω< )⌒★`、`hello`、`hi`、`你好`、`嗨`、`在吗`、`good morning` 等问候；
- 能识别 `谢谢`、`再见`、`你是谁`、`你能做什么` 等简单社交消息；
- 以上回复不编造商品/订单事实，不附带引用；问候后会自然介绍可查商品、价格、库存、订单和售后；
- 带业务词的问候（如“ciallo 血压计多少钱”）不会被当成纯问候，仍走商品问答；
- 无业务词且没有证据的闲聊，不再返回生硬的“没有查到准确信息”，改为友好的能力说明。

部署位置：`/opt/support-suite/current/ai-src-agents-20261106/ai_service`，重启 `support-ai`。
追加备份：`/opt/support-suite/current/ai-src-agents-20261106.backup-20261110-before-social`。

公网验证：

```text
ciallo -> Ciallo～ I'm the CHUNG YIP support assistant...
你好   -> 你好！我是 CHUNG YIP 客服助手...
谢谢   -> 不客气！还有其他想了解的吗？
你是谁 -> 我是 CHUNG YIP 的 AI 客服助手...
```

AI 测试：**244 项通过**，mypy/ruff 通过。商品问答复测仍返回 6 个 `products`，未受影响。

## 追加更新：通用知识问答

2026-11-10 晚继续放开通用知识问答：

- 没有商品、订单、价格、库存、售后等业务信号，也没有本轮 FAQ/商品证据时，交给通用回答提示词；
- 可以回答常识、解释、写作、笑话、翻译等普通问题，例如“法国的首都是哪里”返回“巴黎”；
- 通用回答禁止声称查过商城商品/价格/库存/订单/支付/物流/退款，也禁止诊断、开药或声称执行退款、改地址、发货、转人工；
- 需要实时数据（天气、新闻、汇率）时说明无法访问；
- 涉及商品/订单/售后的消息仍走签名证据和业务工具，不会因为“普通 AI”模式而编造业务事实。

部署位置：`/opt/support-suite/current/ai-src-agents-20261106/ai_service`，重启 `support-ai`。
追加备份：`/opt/support-suite/current/ai-src-agents-20261106.backup-20261110-before-general`。

公网验证：

```text
法国的首都是哪里？ -> 法国的首都是巴黎。
What is the capital of France? -> The capital of France is Paris.
讲个笑话 -> 正常返回一个笑话
ciallo -> Ciallo～ ...
预算300新币，推荐一款血压计 -> 6 个 products 购买链接
```

AI 测试：**248 项通过**，mypy/ruff 通过。

### 通用知识补充：定义与健康解释

进一步区分“通用知识/健康解释”和“业务查询”：

- `是什么/什么是/为什么/怎么调理/what is/why` 等定义或解释类问题，在没有购买、价格、库存、订单、售后、指代词（这个/这款/它）和联系方式证据时，走通用回答；
- 因此“什么是高血压”可以给出通用健康解释，并提示具体诊断咨询医生，不会强行变成商品推荐；
- “这个血压计怎么用”“血压计多少钱”“推荐一款血压计”等仍走商品证据；
- “What is your e-mail address?” 等联系方式问题仍使用 FAQ 证据，不会被通用模式抢答；
- 通用模式不做诊断、不开药、不声称查询业务系统或执行退款/改地址/发货/转人工。

公网验证：

```text
什么是高血压？ -> 通用健康解释 + 就医提醒，citations=0
What is your e-mail address? -> customerservice@chungyip.com，citations=1
法国的首都是哪里？ -> 法国的首都是巴黎。
ciallo -> Ciallo～ ...
预算300新币，推荐一款血压计 -> 6 个 products
```

追加备份：`/opt/support-suite/current/ai-src-agents-20261106.backup-20261110-before-general-guard`。
AI 测试：**250 项通过**，mypy/ruff 通过。
