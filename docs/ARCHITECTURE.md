# 代码结构与依赖规则

## Java 交易服务

顶层以业务能力分包，而不是以技术类型全局分包：

```text
com.zscq.mall.commerce
├── catalog
├── customer
├── inventory
├── order
├── payment
├── promotion
├── support
├── shared
└── config
```

每个业务模块内部遵循：

```text
<module>/
├── api/             HTTP/消息入口、请求响应 DTO
├── application/     用例编排、事务边界、命令与查询
├── domain/          聚合、实体、值对象、领域服务与端口
└── infrastructure/  JPA、Redis、消息、第三方系统适配器
```

允许的依赖方向：

- `api -> application -> domain`
- `infrastructure -> domain`，必要时实现 `application` 定义的端口
- `domain` 不得依赖 Spring MVC、JPA Repository、其他模块的 infrastructure 或 application
- 模块之间只通过公开 API、领域事件或显式端口协作
- `shared` 只放稳定的跨模块概念，禁止成为杂物包

Spring Modulith 验证模块边界，ArchUnit 验证分层依赖。

## Python AI 客服

```text
ai_service/
├── api/             FastAPI 路由、请求响应模型
├── application/     对话用例、工具编排、人工接管
├── domain/          会话、消息、引用、风险与策略模型
├── infrastructure/  模型、向量库、数据库和商城 API 适配器
└── evaluation/      离线数据集、指标和回归评测
```

`domain` 不得导入 FastAPI、SQLAlchemy 或模型供应商 SDK；高风险交易动作只能调用 Spring Boot 暴露的鉴权接口。
