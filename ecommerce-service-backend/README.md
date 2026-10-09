# 电商业务服务（演示）

提供用户最近订单/商品、订单详情/状态、物流及商品信息接口。独立业务服务还包含退款和发货提醒写接口，**没有完整账号鉴权，不得直接公开到公网**；本站 AI 演示网关只允许白名单读取并拒绝所有写操作。

## 环境与安装

需要 Python >=3.11,<3.13（建议 3.12）、uv、MySQL 8。以下命令在本子项目目录执行：

```powershell
uv sync --python 3.12 --frozen
if (!(Test-Path .env)) { Copy-Item .env.example .env }
# 编辑 .env，填写自己创建的专用业务数据库 URL；已有配置不要覆盖。
uv run --frozen python -m app.init_demo --expected-database ecs_business --seed
uv run --frozen uvicorn app.app:app --host 127.0.0.1 --port 18081
```

数据库与账号须先在 MySQL 创建，名称与 --expected-database 一致。初始化只创建缺失表、插入缺失的纯虚构 u1001 演示订单；不会清空、更新已有数据或升级现有表。--seed 可省略。配置自动加载本项目 .env，环境变量优先，缺少 DATABASE_URL 直接报错。密码特殊字符需要 URL 编码。

入口为 `app.app:app`，接口文档 http://127.0.0.1:18081/docs，健康检查 `/health` 会执行实际数据库查询。没有 Compose 文件，不存在 `app.main:app` 入口。

## 主要接口

- GET /health
- GET /users/{user_id}/orders 与 /products
- GET /orders/{order_id}、/status、/logistics
- GET /products/{product_id}
- POST /orders/{order_id}/shipping-reminders 与 /refund-applications（内部演示写接口）

## 检查

```powershell
uv run --frozen python -X utf8 -m unittest discover -s tests -v
```

测试使用内存 SQLite 和 MySQL DDL 编译，不触碰配置中的真实数据库。Dockerfile 仅打包业务 API，需另备 MySQL、传入环境变量并单独初始化。完整架构、授权待确认状态和贡献约定见 [根 README](../README.md)。
