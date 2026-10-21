# Bright Data → Lazada 商品导入

本模块只采集公开的 Lazada 商品详情页，并将结果幂等写入 NOVA 的商家、商品和 SKU 表。API 密钥只通过 `BRIGHT_DATA_API_KEY` 环境变量注入，不写入源码、数据库、请求日志或 Git。

## 已核对的官方接口

资料：

- [Bright Data Lazada Scraper](https://brightdata.com/products/web-scraper/lazada)
- [Bright Data Web Scraper API reference](https://github.com/brightdata/skills/blob/main/skills/bright-data-best-practices/references/web-scraper-api.md)

当前 Bright Data 账号提供的 Web Scraper 数据集 ID：`gd_m6gjtfmeh43we6cqc`。这是账号实际生成的 URL 抓取契约，导入层会从结构化商品字段或页面 JSON-LD 中规范化 Lazada 商品。

### 小批量同步采集

- Method/path: `POST https://api.brightdata.com/datasets/v3/scrape`
- Query: `dataset_id=gd_m6gjtfmeh43we6cqc&notify=false&include_errors=true`
- Header: `Authorization: Bearer ${BRIGHT_DATA_API_KEY}`
- Input: 该账号生成的同步契约使用 wrapper 对象，`input` 中每项包含 `url`，并传 `limit_per_input: null`。

```json
{
  "input": [
    {
      "url": "https://www.lazada.sg/products/example-i123-s456.html"
    }
  ],
  "limit_per_input": null
}
```

- `200` output: 记录数组。优先规范化 `url`、`title/name`、`sku`、`seller_name`、`brand`、`final_price/price`、`initial_price`、`currency`、`stock/availability`、`number_sold`、`rating` 和商品图片字段；若返回通用页面内容，则解析 `application/ld+json` 中的 `Product`、`offers`、`brand`、`seller` 和 `aggregateRating`。两种模式都完整保留原始 JSON。
- `202` output: `{ "snapshot_id": "..." }`，表示转为异步任务。

### 异步进度与结果

- `GET /datasets/v3/progress/{snapshot_id}` → `starting | running | ready | failed`
- `GET /datasets/v3/snapshot/{snapshot_id}?format=json` → 商品记录数组

## NOVA 导入接口

- Method/path: `POST /api/admin/integrations/bright-data/lazada/import`
- Input: 1–20 个 HTTPS Lazada 商品详情 URL；仅允许 Lazada 新加坡、马来西亚、泰国、越南、菲律宾和印度尼西亚域名。

```json
{
  "urls": [
    "https://www.lazada.sg/products/example-i123-s456.html"
  ]
}
```

- Output: 请求数、收到的有效记录数、新建数、更新数、完成时间，以及本地 `productId`、`merchantId`、外部商品 ID 和名称。

```json
{
  "requested": 1,
  "received": 1,
  "created": 1,
  "updated": 0,
  "completedAt": "2026-10-21T00:00:00Z",
  "items": [
    {
      "productId": "00000000-0000-0000-0000-000000000000",
      "merchantId": "00000000-0000-0000-0000-000000000000",
      "externalProductId": "123_SGAMZ-456",
      "name": "Example",
      "created": true
    }
  ]
}
```

## 幂等与追踪

- `products(source_platform, external_product_id)` 是唯一键，同一商品重复导入会更新，不会新增重复商品。
- 商家和本地商品/SKU UUID 由来源与外部 ID 确定性生成，重复运行保持不变。
- 来源 URL、图片、币种、销量、评分、原始 JSON、同步时间和外部 SKU 均保留。
- 外部价格写入 `product_skus`，商品以 `DRAFT` 状态进入待审核，SKU 禁用，显式发布后才对前台可见；重复同步仅更新草稿，已发布或审核中的商品跳过并返回原因。默认直采入口详见 [Lazada 直接采集](./lazada-direct.md)。

## 本地配置

```dotenv
BRIGHT_DATA_API_KEY=replace_with_bright_data_api_key
BRIGHT_DATA_LAZADA_DATASET_ID=gd_m6gjtfmeh43we6cqc
```

不要把真实密钥写入任何受版本控制文件；`.env.example` 只保留占位符。当前用户提供的凭据在 2026-10-21 对官方接口返回 `401 Invalid credentials`，所以在获得 Bright Data 控制台生成的有效 API token 前，真实商品不会写入数据库。
