# 部署指南

## 环境要求

- Docker Engine 27+ 与 Compose v2
- 可访问的 OIDC JWK 地址、PostgreSQL、Redis 和 RabbitMQ
- 独立生成的数据库、消息队列和模型密钥，禁止沿用示例值
- HTTPS 入口和只允许受信来源的跨域策略

## 构建与启动

1. 从 `.env.example` 创建仅部署环境可读的 `.env`，替换所有密码、公开地址和 `OIDC_JWK_SET_URI`。
2. 执行 `make verify`，确认前端、Java、Python、Storybook 和 Compose 配置全部通过。
3. 执行 `docker compose -f docker-compose.yml -f infra/compose/production.yml build`。
4. 执行 `docker compose -f docker-compose.yml -f infra/compose/production.yml up -d`。
5. 检查 `/actuator/health/readiness`、AI `/health`、前台 `/` 和后台 `/healthz`。

Spring Boot 启动时自动执行 Flyway。禁止直接修改已经发布的迁移；结构变化必须新增版本迁移。前端公开 API 地址在构建时写入，域名变更后需要重新构建前端镜像。

## 灰度与回滚

先以 5% 流量灰度 30 分钟，再依次提升到 25%、50% 和 100%。每一档检查错误率、P95、支付回调失败数、订单状态不一致数和人工客服转接率。任一红线触发时停止放量。

应用回滚使用上一版本不可变镜像。数据库迁移默认向前修复，不自动执行破坏性 down migration；若新版本写入了旧版本无法读取的数据结构，按变更单中的兼容窗口和恢复点处理。
