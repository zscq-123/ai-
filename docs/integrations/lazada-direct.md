# Lazada 直接商品采集

默认使用 NOVA 后端直接读取 Lazada 公开页面，不依赖 Bright Data 或其 API key。

## 实际观察到的数据入口

2026-10-21 在新加坡站验证：

| 入口 | 观察结果 | 当前用途 |
| --- | --- | --- |
| `GET https://www.lazada.sg/` | HTTP 200，HTML 内含 `window.__FIRST_SCREEN_DATA` JSON | 已实现公开首页商品列表采集 |
| `GET https://www.lazada.sg/products/pdp-i111650098-s23209659764.html` | HTTP 200，但正文为 `captcha` / `_____tmd_____/punish` 验证页 | 返回明确采集错误；不重试绕过验证 |
| `mtop.lazada.recommend.hp.jfy.service` | 首页 JSON 中的 `__data_url`，标记为 JSONP | 仅观察到接口名；未证明可匿名使用，未集成 |
| `mtop.lazada.kangaroo.core.service.route.lzdPageRecommendService` | 首页 `gcpStartConfig.mtopConfig.pageRecommendApi`，标记为 POST | 仅观察到接口名；未集成 |
| Lazada Open Platform `/products/get` | 官方商品 API | 需要应用与商家授权；当前未提供相应凭证，未调用 |

官方资料：[API 对照表](https://open.lazada.com/apps/doc/doc?docId=108139&nodeId=10397)、[商家授权说明](https://open.lazada.com/apps/doc/doc?docId=108260&nodeId=10533)。当前直采采用页面已公开下发的 JSON，不生成或猜测 MTop 签名。

## NOVA 接口

`POST /api/admin/integrations/lazada/import`（管理员权限）

```json
{
  "urls": ["https://www.lazada.sg/"],
  "limit": 3
}
```

`urls` 支持 SG、MY、TH、VN、PH、ID 六站的官网首页和 `/products/...-i{itemId}-s{skuId}.html` 商品详情，最多 20 个 URL。`limit` 为本次最多入库商品数，范围 1–20，默认 20。首页读取公开 SSR 商品卡片；详情读取公开 `Product` JSON-LD（若有）。URL 去除跟踪参数后去重。

响应保留 `requested`、`received`、`created`、`updated`、`completedAt`、`items`，增加 `skipped` 和每项 `skipReason`。`state` 为 `STAGED_FOR_REVIEW`，全部跳过时为 `UNCHANGED`。`requested` 统计去重后的页面数，`received` 统计本次处理商品数。任何页面触发验证或解析失败，本次事务不会写入部分商品。

独立发布入口：`POST /api/admin/integrations/lazada/products/{productId}/publish`。旧 `/api/admin/integrations/bright-data/lazada/import` 与发布路径保留兼容，但只有明确调用旧导入路径才会请求 Bright Data。

## 字段与数据边界

- `source_platform=LAZADA`，外部商品键为 `站点:商品ID`，例如 `SG:111650098`；重复抓取同一商品更新草稿，不新建重复商品。Bright Data 路径使用同一键规则。
- 首页实际字段：`itemId`、`itemUrl`、`itemTitle`、`itemDiscountPrice`、`itemPrice`、`itemCurrentStock`、`itemImg`。
- 价格按原币种存储，SG 对应 SGD，不把新加坡元显示成人民币；JSON-LD 使用 `priceCurrency`。`AggregateOffer.lowPrice` 不能作为具体 SKU 售价，故不导入仅含价格区间的详情。
- 缺少具体库存数时记录为 0，不根据 `InStock` 或 `itemHaveStock` 编造数量。首页活动销量仅保留原始记录，不当作商品历史总销量。
- 首页未公开商家身份的条目标为 `Lazada SG · 待确认商家` 等待审核；不声称是已入驻或已授权商家。
- 新商品状态为 `DRAFT`，新商家为 `PENDING_REVIEW`，SKU 禁用；导入不自动上架。重复同步只更新草稿，已上架和审核中的外部商品保持现状，响应说明先手动转为草稿再同步。草稿同步和发布都会递增商品版本，旧的商家编辑表单会收到版本冲突。
- `source_url` 是真实商品 URL，`source_payload` 包含 `provider=LAZADA_DIRECT`、`format`、`fetchedFrom`、`fetchedAt` 和原始商品记录，`source_last_synced_at` 保存入库时间。
- 主图保存到 `source_image_url`；`image_urls` 只在原字段为空时填充，避免覆盖商家自己上传、排序或清空后的图片。
- 重采根据商品所属 SKU 的实际 ID 更新，保留商家修改过的 `sku_code`；只有尚无 SKU 时创建一个。存在多个 SKU 时要求显式映射，整次导入回滚，避免将一个外部价格错误应用到多个规格。

## 运行约束

只允许 HTTPS 官网域名和支持的页面路径，拒绝自定义端口、URL 用户信息和任意子域。HTTP 客户端不携带登录 Cookie、Bright Data 密钥，不跟随重定向；验证码、403、429 等直接报告失败。单页上限 3 MB，默认请求超时 20 秒，多页面请求间隔 1 秒。

可通过 Spring 环境配置覆盖 `integrations.lazada-direct.timeout` 与 `integrations.lazada-direct.request-interval`，无需密钥。

## 验证

首轮通过 13 项相关测试：公开首页字段解析、JSON-LD 解析、来源追踪、库存未知处理、重复商品去重、URL 限制、验证页中止、HTTP 不跳转与默认直采/显式 Bright Data 选择。另补充已发布商品跳过、行锁与零写入回归测试。

2026-10-21 11:57:19（Asia/Shanghai）通过新直采 HTTP 接口实际导入 3 件首页公开商品，响应 `created=3`、`updated=0`：

| 外部商品 ID | 商品 | 原币种售价 |
| --- | --- | --- |
| `SG:111650098` | MILO UHT Chocolate Malted Milk Original（4 × 6 × 200 ml） | SGD 30.90 |
| `SG:128150790` | MAC Macximal Silky Matte Lipstick | SGD 41.00 |
| `SG:128486329` | MAC Studio Fix Powder Plus Foundation | SGD 71.00 |

数据库回读确认：均为 `DRAFT`，`source_currency=SGD`，每件 1 张主图，SKU `enabled=false`，商家 `PENDING_REVIEW`，来源提供者 `LAZADA_DIRECT`，原始记录抓取时间 `2026-10-21T03:57:19.390075Z`。这些是当时公开页面的记录，价格和外部活动库存会变化。

12:04 再次通过最终代码调用同样请求：`created=0`、`updated=3`、`skipped=0`；随后接口回读三件商品均仍为 `DRAFT`、SGD、1 张图片、版本 1，未生成重复商品。最终外部商品相关 16 项测试通过（含保留实际商家归属、已上架商品不覆盖、保留手工 SKU 编码的回归）。
