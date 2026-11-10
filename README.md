# Enterprise Commerce Platform

企业级网络商城，包含消费者商城、运营管理台、Spring Boot 交易后端和 Python AI 客服。

## 工程结构

```text
apps/storefront            Next.js 消费者商城
apps/admin                 React + Vite 运营管理台
services/commerce-api      Spring Boot 交易核心
services/ai-service        Python + FastAPI AI 客服
public/brand               品牌和 Image 2.5 概念资产
docs                       架构与开发文档
```

Java 服务按业务模块拆包，每个模块内部使用 `api / application / domain / infrastructure` 分层。Python 客服使用相同的依赖方向，具体规则见 [架构说明](docs/ARCHITECTURE.md)。

## 本地启动

1. 复制 `.env.example` 为 `.env`。
2. 执行 `make infra-up` 启动 PostgreSQL、Redis 和 RabbitMQ；需要本地对象存储时再执行 `make storage-up`。
3. 执行 `pnpm install && pnpm dev` 启动前端。
4. 在 `services/commerce-api` 执行 `./mvnw spring-boot:run`。
5. 安装 AI 服务依赖后执行 `uvicorn ai_service.main:app --app-dir services/ai-service/src --reload`。

## DeepSeek 客服

AI 客服默认使用 DeepSeek OpenAI 兼容接口。将轮换后的密钥写入本地 `.env` 的
`DEEPSEEK_API_KEY`，并保持 `AI_PROVIDER=deepseek`；默认模型为 `deepseek-flash`。
密钥缺失或模型接口暂时不可用时，服务会降级为受知识库约束的本地规则回答，不会把密钥写入日志或前端代码。
客服主回答默认关闭 DeepSeek 思考模式（`AI_THINKING=false`），与 Agent JSON 调用保持一致；这样 `deepseek-flash` 的推理 token 不会挤占商品推荐、对比等长答案。需要模型推理时可设为 `AI_THINKING=true`。

### 本机 MLX + LoRA 候选

Apple Silicon 本机可用 OpenAI 兼容的 MLX 服务加载当前离线候选：

```bash
.venv/bin/mlx_lm.server \
  --model data/models/Qwen3-4B-Instruct-2507-4bit \
  --adapter-path data/training/selected/qwen3-4b-customer-service-candidate-v1 \
  --host 127.0.0.1 --port 18080 --temp 0 --max-tokens 400
```

随后给 AI 客服进程设置：

```bash
AI_PROVIDER=mlx
AI_MODEL=data/models/Qwen3-4B-Instruct-2507-4bit
AI_MODEL_BASE_URL=http://127.0.0.1:18080/v1
AI_PERSIST_CONVERSATIONS=false
```

该模式只用于本机试训验收。`mlx_lm.server` 自带的 HTTP 服务没有生产级安全能力，不能直接暴露到公网。

### NOVA 实时客服工具

AI 客服通过 Commerce API 的只读内部接口获取实时库存、当前用户订单、物流和支付状态，
不直接连接商城数据库。为两个服务配置同一个独立密钥：

```bash
COMMERCE_SUPPORT_TOOL_SECRET=replace_with_a_different_32_char_secret
AI_COMMERCE_TOOL_SECRET=replace_with_a_different_32_char_secret
```

商城前台只把服务端校验后的客户 ID，以及当前商户、商品和 SKU 上下文签名后交给 AI 服务；
订单、物流和支付查询始终限制在当前客户，传入商户时再增加商户范围。库存引用使用
`inventory://`，订单、物流和支付分别使用 `order://`、`logistics://`、`payment-status://`。

商户记录真实运单使用 `PUT /api/seller/{merchantId}/orders/{orderNo}/shipment`，需要该商户的
SELLER/ADMIN 身份。迁移 `V17__order_shipments.sql` 会创建标准运单表；未写入运单时，客服只能说明
当前订单是否已发货，不能编造承运商、单号或物流节点。

客服的表达方式由 `services/ai-service/src/ai_service/prompts/library.py` 中的场景话术卡统一约束：
运行时按意图自动选择话术卡，把表达规范、禁忌与范例注入提示词，再叠加检索到的知识。
话术手册见 [话术手册](docs/话术手册.md)；修改话术后执行 `make scripts` 重新导出。

知识检索默认使用本地向量模型 `BAAI/bge-small-zh-v1.5`（fastembed + ONNX，CPU 推理），
先用 624 条已标注意图样例做三近邻路由，并保留向量/关键词融合降级；范围外问题返回无知识，
不强行附会最近政策。首次使用执行 `make embeddings` 下载模型（约 90 MB），默认持久缓存到
`~/.cache/nova/fastembed`，之后可完全离线运行；可用 `AI_EMBEDDING_CACHE_DIR` 覆盖缓存目录。
设置 `AI_RETRIEVER=keyword` 可退回纯关键词检索。

商品知识可用 Bright Data 抓取后转成知识条目：

```bash
.venv/bin/python scripts/brightdata_lazada_pull.py --limit 12   # 抓取并解析 JSON-LD
.venv/bin/python scripts/products_to_knowledge.py --translate    # 译成中文并入知识库
```

产出 `services/ai-service/knowledge/products.jsonl`，用 `AI_KNOWLEDGE_FILE` 指向即可加载。

运营管理台的“AI 客服”页面支持上传 FAQ 知识文件。导入内容先保存为草稿，运营审核并点击发布后，
才会进入商城客服的“常见 F&A”卡片和 AI 检索范围。格式与模板见
[FAQ 知识库导入说明](docs/FAQ知识库导入说明.md)。

## 质量验证与部署

执行 `make verify` 可一次完成前端 lint、类型检查、生产构建、Storybook、Java 测试与打包、Python 静态检查与测试，以及生产 Compose 配置校验。

客服对话质量用 `make eval` 回归（需先启动 ai-service）：逐条检查意图、风控门禁、引用、语气与长度，并生成 [评测报告](docs/评测报告.md)。

部署、备份恢复、安全与发布边界分别见：

- [部署指南](docs/DEPLOYMENT.md)
- [运行手册](docs/RUNBOOK.md)
- [备份恢复](docs/BACKUP_RESTORE.md)
- [安全基线](docs/SECURITY.md)
- [发布验收清单](docs/RELEASE_CHECKLIST.md)

六个工程阶段已经形成可运行基线；真实支付、真实身份、消息通道、对象存储和生产等价压测仍必须在目标环境完成，不能由本地构建结果替代。
