# 本地 OMS / BUZUD AI 客服接入

更新：2026-11-09。三个项目通过服务端 HTTP 接入，共用本项目的模型、话术、事实审核与风险判断。

| 应用 | 用户入口 | 后端接口 | AI 接口 |
| --- | --- | --- | --- |
| OMS 管理端 | `/support`，左侧「AI 客服」 | `POST /api/v1/support/chat` | `POST /v1/integrations/oms/chat` |
| medical-sg.com | 右下角客服浮窗 | `POST /api/v1/chat/messages` | `POST /v1/integrations/buzud/chat` |

两端请求均为 `{ "message": "这个订单什么状态？", "orderNo": "可选订单号", "conversationId": "可选 UUID" }`。
OMS 返回标准 `code/message/data`，`data.answer` 为答案；独立站保留 `reply` 字段，增加 `citations`、`requiresHuman`、`degraded`。
独立站继续将问答写入原聊天记录表，记录认证后的用户 ID。页面为当前会话生成随机 UUID；AI 服务按来源、认证用户 ID、会话 UUID 保存最近问题和话题提示（30 分钟过期，最多 1000 个会话）。页面刷新产生新会话；重启 AI 会清除提示。当前为单进程本地会话缓存，部署多实例时需改用共享存储。

重复、代词追问会沿用最近问题或话题，所有 FAQ 和订单证据仍逐轮从业务端重新读取；不缓存或复述旧模型答案作为事实。未携带 conversationId 的调用保持单轮行为。

## 数据与权限

- OMS 网关本地 Controller 单独校验 JWT（Gateway GlobalFilter 不覆盖本地 Controller）。读取订单时只转发 Bearer Token，并再次校验商户归属。管理账号遵循现有管理员订单权限。
- 独立站复用 `OrderService.get(currentUserId, orderNo)`；匿名订单查询返回 401，他人订单遵循原服务的归属校验。
- 传给 AI 的订单字段仅有订单号、状态、金额、币种。姓名、手机号、地址、备注不传入模型。未取得物流轨迹、退款到账记录时不推断。
- 明确查询订单状态时，使用本次签名证据中的订单状态和金额生成确定性摘要，并附对应订单来源；防止模型在已有核验记录时仍误答「没有记录」。
- BUZUD FAQ 候选取自本站既有客服知识库（当前 7 条，单次最多 10 条），AI 按关键词、常见英文表达及会话话题筛选。外部接口不访问 NOVA 商城的知识库、订单工具或数据库，避免串店数据。
- 两个来源使用不同密钥。签名覆盖 `source + "\n" + epochSeconds + "\n" + 原始 UTF-8 JSON`，算法 HMAC-SHA256，时间窗口 120 秒。浏览器不得持有签名密钥，也不能提交可信身份或证据。
- 当前接入只查询与答复；独立站需要人工时显示现有客服工单入口。不会因 AI 回答而执行退款、改地址、发货等操作。
- 已取消订单的付款追问会明确无需继续付款，并区分取消和退款到账。物流答复使用对应应用入口；不存在订单时 OMS 提示核对订单号，不再误报连接故障。
- 商品实时价格与库存已接入独立站客服：后端从完整商品目录中按问题挑选商品，随签名证据传入（`catalog://buzud/{productId}`）；明确要求全部商品时返回分段完整清单（`catalog://buzud/index/{n}`）。AI 只依据本轮证据回答价格、规格、用法、对比和推荐，资料缺失时明确说明，不补全参数。
- 商品页上下文由浮窗随请求提交（`productSlug`），用于回答“这个/这款”。存在 OMS SKU 映射时，明确询问库存会实时读取 OMS 可售库存，读取失败退回最近快照；没有映射或 OMS 未启用时提示以商品页和结算结果为准，不声称有货。浏览类问题返回类目概览和全部商品页入口。
- 中文需求可反推英文商品：匹配会读取商品适用人群/说明，并区分设备与配件/耗材（设备类需求优先主机）。目录没有的品类明确说明没有；屏幕大小、操作难易等资料未提供的属性不推断。
- 独立站聊天响应新增 `products` 商品购买链接数组（名称、价格、图片、商品页 URL），前端渲染为带「去购买」的商品卡片；只对回答确实提到的商品生成，否定/无匹配回答不附带卡片。
- 优惠发放仍未接入商品工具；涉及优惠券时继续引导到领券中心，不承诺折扣或已发券。

## 分开运行的配置

AI 服务：设置 `AI_OMS_INTEGRATION_SECRET`、`AI_BUZUD_INTEGRATION_SECRET`。
客服主回答默认关闭 DeepSeek 思考模式（`AI_THINKING=false`），与 Agent JSON 调用一致；`deepseek-flash` 实测可稳定输出商品推荐和目录回答，需要推理时可设为 `true`。
OMS 网关：`NOVA_AI_URL=http://127.0.0.1:18000`，`NOVA_AI_SECRET` 与 AI 的 OMS 密钥相同。
BUZUD 后端：同一个 `NOVA_AI_URL`，`NOVA_AI_SECRET` 与 AI 的 BUZUD 密钥相同。
OMS 可用 `OMS_SUPPORT_GATEWAY_URL` 指定读取订单的网关地址，默认为当前服务端口。
密钥为空时外部 AI 接口返回 503；独立站显示明确不可用提示，不伪装为模型已回答。

## 一起启动

依赖已初始化的本地 OMS MySQL（13306）、Redis（16379）、Nacos（8848）及 BUZUD PostgreSQL（5432）。
当前机器使用 Colima：先执行 `colima start`，已有容器会按原重启策略恢复。

分别构建两个后端：

```bash
cd /Users/yangyongze/Documents/ChatGPT/oms/backend
mvn -q -pl oms-gateway,user-service,order-service -am package -DskipTests
cd /Users/yangyongze/Documents/ChatGPT/独立站medical-sgcom/ikeas/backend
./mvnw -q package -DskipTests
cd /Users/yangyongze/Documents/ChatGPT/ai客服
.venv/bin/python scripts/run_local_support_integration.py
```

启动器仅启动本轮接入所需的 AI、OMS 网关/用户/订单服务、BUZUD 后端、两个前端。OMS 其余业务页面仍需其对应服务。
密钥每次启动随机生成，仅注入子进程环境；日志在 gitignored 的 `data/integration-local/`，不会打印密钥。
端口被占用时拒绝重复启动。Ctrl-C 关闭本启动器创建的应用进程，保留数据库容器和数据。

- OMS：`http://localhost:5173/support`，使用原本地账号登录。
- 独立站：`http://localhost:3000/zh/`，右下角客服。
- AI：`http://127.0.0.1:18000/health`。

AI 沿用本项目 `.env` 的模型配置（当前 DeepSeek）。离线 LoRA 候选未随本次接入启用。

## 验证

`services/ai-service/tests/test_integrations.py` 覆盖来源密钥隔离、签名篡改、过期时间、匿名订单、跨请求证据隔离、额外身份字段及模型过度拒答时的状态摘要。
OMS `SupportControllerTest` 覆盖 JWT、商户越权、隐私字段过滤、Spring Boot 4 响应序列化。
BUZUD `ChatControllerTest` 覆盖身份来源、匿名查询、订单归属、隐私字段过滤与断线提示。

```bash
node scripts/smoke_local_support_integration.mjs
```

浏览器冒烟使用本地 OMS 演示管理账号，只读取已有订单；检查 OMS 页面答案中的订单号、实际状态和来源，BUZUD 窄屏 FAQ 回答及匿名订单拒绝。
结果与截图保存为 `data/integration-local/browser-smoke.json`、`oms-support.png`、`buzud-support-mobile.png`。
这些是本地接入验证，不代表生产发布或真实人工已经接通。

2026-11-06 本地验证：AI 接入及原聊天测试 17 项、OMS 接入测试 3 项、BUZUD 接入测试 4 项通过。浏览器读取实际 OMS 订单并核对「已取消」状态通过，390px 窄屏 FAQ 和匿名订单 401 检查通过。BUZUD 已登录客户订单流程由后端测试覆盖，本轮未使用真实客户账号做浏览器验证。
