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

## 质量验证与部署

执行 `make verify` 可一次完成前端 lint、类型检查、生产构建、Storybook、Java 测试与打包、Python 静态检查与测试，以及生产 Compose 配置校验。

部署、备份恢复、安全与发布边界分别见：

- [部署指南](docs/DEPLOYMENT.md)
- [运行手册](docs/RUNBOOK.md)
- [备份恢复](docs/BACKUP_RESTORE.md)
- [安全基线](docs/SECURITY.md)
- [发布验收清单](docs/RELEASE_CHECKLIST.md)

六个工程阶段已经形成可运行基线；真实支付、真实身份、消息通道、对象存储和生产等价压测仍必须在目标环境完成，不能由本地构建结果替代。
