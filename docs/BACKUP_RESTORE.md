# PostgreSQL 备份与恢复演练

## 每日备份

使用部署平台的密钥注入机制提供连接信息，执行自定义格式备份：

```bash
pg_dump --format=custom --no-owner --file commerce-$(date +%F).dump "$DATABASE_URL"
```

备份文件必须加密、跨故障域保存，并设置保留周期和访问审计。每天验证文件可读，每月至少执行一次隔离恢复演练。

## 隔离恢复

1. 创建空的演练数据库，绝不覆盖生产库。
2. 执行 `pg_restore --clean --if-exists --no-owner --dbname "$RESTORE_DATABASE_URL" backup.dump`。
3. 启动同版本应用，验证 Flyway、核心表数量、抽样订单金额、支付回调唯一键和审计记录。
4. 记录恢复耗时、数据时间点和校验结果，演练库确认后销毁。

未经双人复核，不得把 `RESTORE_DATABASE_URL` 指向生产数据库。
