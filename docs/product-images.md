# 商户商品图片与编辑页

入口：本地 `http://127.0.0.1:5175/` → 我的商品 → 编辑 / 添加商品。

## 交互与存储

- 商品编辑采用分区表单 + 右侧买家预览；分组侧栏参考卖家中心信息结构。
- 遵循 Apple 风格的系统字体和清晰内容层级；Liquid Glass 仅用于导航、分区工具栏和底部保存栏，表单使用不透明背景。
- 最多 9 张图片；文件选择、拖放上传、进度、失败重试、排序、设为封面、移除均已接入。第一张即封面，点击保存后持久化。
- 支持 PNG / JPEG / WebP。每个源文件不超过 5 MiB、最长边 6000 像素、总像素不超过 1600 万；后端解码并重新编码，剥离原文件名、EXIF 和尾部附加内容。
- 图片按商户隔离；不能将其他店铺上传的文件绑定到本店商品。原始外部商品图片仅允许保留/排序/移除，不能任意注入外链。
- 元数据在 PostgreSQL `product_media`，文件在 `services/commerce-api/data/product-images/`，由 `commerce.media.storage-path`（环境变量 `PRODUCT_MEDIA_STORAGE_PATH`）配置。本地文件与数据库需一起备份；当前不是云对象存储/CDN。
- 商品有序图片存储在 `products.image_urls`，`[]` 表示商户主动清空，不回退旧的导入图片。
- 商品列表、商城首页推荐、搜索、频道页、店铺页、详情图库与新加入购物车的条目消费实际封面。外部价格保留原币种。

## 接口

| 方法与地址 | 内容 |
| --- | --- |
| `POST /api/seller/{merchantId}/media/product-images` | multipart 字段 `file`；返回 `id,url,contentType,width,height,sizeBytes` |
| `GET /api/public/media/product-images/{id}` | 读取清洗后的图片，公开访问、不可变缓存 |
| `GET /api/seller/{merchantId}/products/{productId}` | 编辑详情、版本、图片与币种 |
| `PUT /api/seller/{merchantId}/products/{productId}` | 携带 `expectedVersion`、商品字段和有序 `imageUrls` 保存 |
| `POST /api/seller/{merchantId}/products` | 保存新商品草稿 |
| `GET /api/public/categories` | 可用商品分类 |

生产环境依赖已有卖家 JWT/商户权限。`LOCAL_ADMIN_PUBLIC=true` 仅用于本机联调，不可在公网环境启用。新建草稿不等同于商品上架；本阶段未添加视频上传、裁剪和多规格编辑。

## 并发保护

商家保存与订单扣减库存统一先锁商品行。扣减库存递增商品版本；旧编辑表单保存返回 409，不能用旧库存覆盖已完成的扣减。商品更新保留 SKU 启用状态和来源币种。

## 2026-10-21 验收记录

- 浏览器实际选择两张本地示例 PNG → 上传 → 第二张设为封面 → 保存成功。
- 接口回读顺序、首图与版本正确；重新打开商户编辑页仍显示已保存图片。
- 买家详情显示两张真实文件，点击第二张后 `naturalWidth > 0`，图库计数从 `1/2` 变为 `2/2`。
- 桌面 1280px 与手机 390px 检查；手机内容宽度等于 390px，无整页横向溢出。
- 伪装为 PNG 的文本文件返回 400；错误商户读取返回 403；旧版本保存返回 409。
- 测试后恢复原商品全部业务字段与原图片列表，不将示例图保留为商品照片；上传文件仍作为未关联的测试媒体留在本地。
- 商户端 typecheck/lint/build、商城 typecheck/lint/build、管理端 typecheck/lint 全部通过。
- 后端全套 50 项通过；追加外部 SKU 重采回归后相关 16 项再通过，最终报告累计 51 项，0 失败/错误/跳过。真实 PostgreSQL 并发测试包含 3 个锁顺序场景；测试 schema 已清理。
- 当前 JDK 27 有旧 ArchUnit 字节码识别和 Mockito agent 警告，不能将该环境的架构测试通过等同于完整的架构扫描；业务与并发测试通过情况单独记录。
