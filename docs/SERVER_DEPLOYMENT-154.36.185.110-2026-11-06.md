# OMS、独立站与 AI 客服服务器部署

2026-11-06 完成，服务器 `154.36.185.110`。

后续按用户要求新增普通测试账号 `customer_test`（CUSTOMER，未绑定邮箱）。已从公网验证登录、个人资料和订单列表均返回 200，个人中心正常显示测试用户；已登录访问不存在订单返回 404。密码单独保存在本地私有凭据文件中，不写入本报告。

## 访问与验收

| 项目 | 地址 | 本次验证 |
| --- | --- | --- |
| 独立站 | https://154.36.185.110:18083/ | HTTPS、移动页面、客服入口、中文/英文/多轮对话 |
| 独立站 CMS | https://154.36.185.110:18083/admin/ | 随机密码登录、会话、统计接口与管理页面 |
| OMS | https://154.36.185.110:18084/ | 随机密码登录、客服页面、业务接口 |
| OMS 客服 | https://154.36.185.110:18084/support | 能力说明、隐私拒绝、无效订单与身份校验 |

管理账号均为 `admin`，使用两套不同的随机密码。凭据保存在本地 `data/deployment-154-20261106/服务器访问说明.md`，权限为 `0600`，未进入版本控制。

真实 Chrome 公网验收 **20 项通过，0 项失败**。原始结果与截图在 `data/deployment-154-20261106/public-acceptance/`。覆盖八个 OMS 接口：当前用户、订单、SKU、库存、售后、支付、通知、库存导入模板；以及中英文客服、多轮追问、人工工单入口说明、拒绝伪造退款结果、匿名和无效令牌拦截。

七个 OMS Java 服务、独立站后端、专用 AI 服务均返回 HTTP 200；详细记录在 `data/deployment-154-20261106/health-acceptance.json`。独立站、OMS、原 NOVA 公网页面最终均返回 200。302 个本地静态文件与部署文件 SHA-256 全部一致。

本地 OMS 后端完整构建：128 项测试通过。OMS 前端类型检查、lint、构建通过。独立站 Linux amd64 版本构建通过，已排除嵌套目录中的本地环境文件；Linux 原生 sharp 加载通过。之前的 AI/独立站接入回归记录见 `LOCAL_SUPPORT_FIXES-2026-11-06.md`。

## 服务器配置

- 发布目录：`/opt/support-suite/releases/20261106-support`。
- 当前版本：`/opt/support-suite/current`。
- Compose：`compose.json`，项目名 `support-suite`，共 12 个容器。
- 私有配置和 CMS 数据：`/opt/support-suite/shared`。服务密码、JWT 密钥、两组 AI HMAC 密钥独立生成。
- 复用现有 MySQL/PostgreSQL 实例，新增独立账号与业务库；独立 Redis 容器。业务 API 和数据库未映射到公网。
- OMS 使用容器内静态服务发现；没有增加 Nacos/RocketMQ 进程。当前业务代码不调用 RocketMQ。
- HTTPS 使用服务器现有的 IP 证书；`support-suite-certificate.timer` 每日两次重新加载证书，与原证书续期任务配合，已执行 reload 验证。
- AI 使用专用进程和现有运行镜像，只开放 OMS/BUZUD 签名接入路由。当前模型为 `deepseek-flash`；未切换自训练 LoRA。

## 已处理的部署故障与容量

初次并发启动时，4 GB 主机出现内存压力和全局 OOM，原 NOVA commerce-api 自动重启一次。随后降低新 Java 服务的内存配置、改为逐个启动，将原先的 `vm.swappiness=0` 调整为 60。调整后服务恢复健康，后续内核检查未发现新的 OOM。

最终观察：约 3.1 GB 物理内存占用、约 0.77 GB 可用内存、约 1.1 GB Swap 已使用，磁盘约 3 GB 可用。本次是功能验收，未进行负载测试或整机重启测试，不能据此判断生产并发容量。启动阶段还修复了 AI 源文件权限和 Sentinel 日志目录权限；专用 AI 的历史重启计数来自这次权限修复前的重试。

## 业务边界

- 新建环境未迁移旧站客户、历史订单或旧 OMS 库存。真实已有订单的逐单问答在此前本地测试中验证；本次公网验证了无效订单、权限与列表接口，未创建或操作真实订单。
- 独立站与 OMS 的 AI 客服已接通；独立站到 OMS 的订单/商品同步保持关闭，尚未建立新环境商户及 SKU/库存映射。
- 未启用真实支付、物流下单或邮件发送；OMS 保留模拟集成配置，独立站关闭模拟付款和未配置的真实收银台。通知服务采用 mock，因此不执行 SMTP 健康检查。
- 实时商品价格/库存、可用优惠券工具仍属于此前记录的能力缺口，客服不会编造查询结果。
- 未迁移 `medical-sg.com` / `oms.medical-sg.com` 域名。

## 运维与回退

部署配置和辅助脚本在 `deploy/support-suite/`，凭据不在该目录。

```sh
cd /opt/support-suite/current
docker compose -f compose.json ps
python3 start_backends.py  # 逐个启动/更新 Java 服务并等待健康检查
docker compose -f compose.json logs --tail 100 support-ai
python3 backup.py
```

首份备份：`/opt/support-suite/backups/20261106T071859Z`，包含新增业务库、CMS 数据和私有配置，目录仅 root 可访问，压缩文件完整性检查通过。

若需要停止本次部署，运行 `docker compose -f compose.json down`，保留业务库和 shared 数据，不删除数据库或现有应用容器。专用证书重载定时器可单独停用。内存策略记录在 `/etc/sysctl.d/90-support-suite-memory.conf`；停止新服务后才应评估是否恢复原值，避免再次触发内存压力。

## 后续更新（2026-11-09）

独立站商品目录问答已接入：客服从完整商品目录读取商品名称、价格、规格、用法、注意事项和商品页链接；存在 OMS SKU 映射且启用 OMS 时可返回实时可售库存，否则明确提示以商品页/结算页为准。优惠券工具仍未接入。实现与验证见 `docs/LOCAL_SUPPORT_INTEGRATION.md` 及独立站 `docs/AI客服接入.md`。
