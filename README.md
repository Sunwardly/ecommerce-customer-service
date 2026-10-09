# 电商智能客服 · 电商小二

基于 Vue 与 FastAPI 的电商客服演示项目，通过多轮文字对话和订单卡片查询演示订单、物流与商品信息。

![状态：演示项目](https://img.shields.io/badge/status-demo-818cf8)
![Vue 3](https://img.shields.io/badge/Vue-3-7dd3fc)
![FastAPI](https://img.shields.io/badge/backend-FastAPI-818cf8)
![私有仓库](https://img.shields.io/badge/repository-private-lightgrey)
[![Checks](https://github.com/Sunwardly/ecommerce-customer-service/actions/workflows/checks.yml/badge.svg)](https://github.com/Sunwardly/ecommerce-customer-service/actions/workflows/checks.yml)



**本项目以私有仓库维护。根 LICENSE 是授权待确认声明，不是开源许可证。** 原教学代码和图片、视频的再发布权限仍需维护者确认，见 [资源与授权](docs/资源与授权.md)。

## 核心功能

- **多轮文字客服**：LLM 规划 task / knowledge / chitchat 三条处理路径，经过校验后执行任务、知识问答或闲聊。
- **可配置业务流程**：使用 YAML 定义流程、步骤和槽位，由对话状态机推进。
- **订单与商品卡片**：展示演示用户的对象列表，支持将卡片发送给客服。
- **订单详情介绍**：发送订单后直接查询状态、商品明细、金额、下单时间和最新物流；缺失或失败时明确提示。
- **访客对话隔离**：服务端签名 Cookie 绑定身份，支持刷新恢复历史和开启新对话，拒绝冒用其他访客身份。
- **演示数据边界**：仅查询 `u1001` 演示列表中的订单、商品；站点业务网关拒绝退款等写操作。
- **响应式聊天界面**：石墨蓝紫配色、连续消息列表、本地客服头像；手机使用紧凑顶部栏和可展开的订单/商品面板。

### 当前边界

- 退款、转人工与相似商品推荐尚未接入完整真实业务，不代表已提交申请、接通客服或生成真实推荐。
- FAQ / RAG provider 目前返回占位结果，**没有已完成的知识库检索或向量数据库集成**。
- 数字人前端与后端接入代码存在，但不是当前开发重点。本机缺少后端云 SDK，不能据此声称真实音视频已可用。
- 当前 `DEMO_ACCESS_REQUIRED=False`，页面无需访问口令；访客隔离和演示业务权限仍生效。此项目尚不具备完整账号体系和生产部署方案。

## 技术栈与架构

| 部分 | 技术与职责 |
| --- | --- |
| 前端 | Vue 3、Vite 6、JavaScript；主界面位于 `src/App.vue` |
| AI 客服后端 | FastAPI、Uvicorn、Pydantic、LangChain / langchain-openai；规划、校验、流程执行、历史管理 |
| AI 状态持久化 | SQLAlchemy 异步会话、aiomysql、MySQL，保存 `dialogue_states` |
| 电商业务后端 | FastAPI、SQLAlchemy 同步会话、PyMySQL、MySQL；订单、商品和物流接口 |
| 配置与模板 | pydantic-settings、PyYAML、Jinja2 |
| 服务通信 | HTTPX 调用业务接口；数字人聊天路径另有 WebSocket 接口 |
| 测试 | Python 标准库 unittest、FastAPI TestClient；另有流程与步骤自检脚本 |

```text
浏览器 → Vue / Vite :5174
              ├─ /api、/commerce → AI 客服后端 :18082
              └─ /ws            → AI 客服 WebSocket
                                      ├─ HTTP → 电商业务后端 :18081 → 业务 MySQL
                                      ├─ AI 对话状态数据库
                                      └─ OpenAI 兼容的 LLM 接口
```

AI 后端通过 HTTP 消费电商业务数据，**不直接访问业务表**。AI 对话状态存储与业务存储须按各自配置准备。

## 环境要求

| 环境 | 要求 |
| --- | --- |
| Python | AI 后端要求 `>=3.12`；业务后端要求 `>=3.11,<3.13`。两者可分别使用 Python 3.12 虚拟环境 |
| Node.js / npm | 建议 Node 22.13+ 或 Node 24+（新加入的 ESLint 10 要求）；本机验证 Node 24.15.0 |
| 数据库 | 可访问的 MySQL 8.x、已建立的数据库与表、有效账号权限 |
| LLM | 可访问的 OpenAI 兼容接口、有效模型名与 API Key |
| 开发工具 | Git、uv（复现 Python 锁文件）；业务后端已有 Dockerfile，没有 Compose 文件 |

本机 AI 后端使用 Python 3.13.13，业务后端运行在独立虚拟机容器中。不要把该 Python 3.13 环境用于要求 `<3.13` 的业务后端。

下文命令采用 **Windows PowerShell**，每个服务使用独立终端。TODO 参数必须替换，不能原样用于实际启动。

## 安装与本地启动

### 1. 进入项目

首次下载：

```powershell
git clone https://github.com/Sunwardly/ecommerce-customer-service.git
cd ecommerce-customer-service
```

私有仓库需要已授权的 GitHub 账号。已有本地源码时，本机路径如下，其他机器替换为自己的目录：

```powershell
Set-Location D:\QWER\Projects\ecommerce-customer-service
```

仓库地址：[Sunwardly/ecommerce-customer-service](https://github.com/Sunwardly/ecommerce-customer-service)，默认分支 `main`。空的 `main.py` 不是应用入口。

### 2. 准备数据库与演示数据

两个服务启动时不会自动建表。请先在 MySQL 创建两个专用数据库（初始化工具不会创建数据库或用户）：

```sql
CREATE DATABASE IF NOT EXISTS ecs_business CHARACTER SET utf8mb4;
CREATE DATABASE IF NOT EXISTS ecs_ai CHARACTER SET utf8mb4;
```

配置独立数据库账号、按需授予权限，避免共用 root。首次初始化账号需要 CREATE 权限；正常运行账号只需业务所需读写权限。
下面的初始化命令会核对数据库名，只创建缺失表，不删除数据、不修改已有表；`--seed` 只新增缺失的虚构 u1001 数据，重复执行不覆盖已有记录。不要在真实业务库中导入演示数据。

已有可用业务中台时，可跳过业务安装与种子导入，AI 配置直接指向该中台。已有表的结构升级需要单独的迁移方案，`create_all` 不会自动迁移。

### 3. 安装并启动电商业务后端

从项目根目录打开终端：

```powershell
cd .\ecommerce-service-backend
uv sync --python 3.12 --frozen
if (!(Test-Path .env)) { Copy-Item .env.example .env }
# 编辑 .env，填写自己新建的数据库连接信息和有效配置。已有 .env 时不要覆盖。

# .env 的数据库名与 --expected-database 必须一致。
uv run --frozen python -m app.init_demo --expected-database ecs_business --seed
uv run --frozen uvicorn app.app:app --host 127.0.0.1 --port 18081
```

该服务从项目自己的 `.env` 加载配置，进程环境变量优先；`DATABASE_URL` 没有默认口令，缺少时会明确报错。密码中的 URL 特殊字符需要编码。`APP_HOST`、`APP_PORT` 可供 `main.py` 使用；上面的 Uvicorn 命令明确指定监听地址与端口。

验证：

```powershell
Invoke-RestMethod http://127.0.0.1:18081/health
```

业务 API 文档：<http://127.0.0.1:18081/docs>。真实应用对象为 `app.app:app`，不是旧文档中的 `app.main:app`。

### 4. 安装并启动 AI 客服后端

从项目根目录打开另一个终端：

```powershell
cd .\customer-service-backend
uv sync --python 3.12 --frozen
if (!(Test-Path .env)) { Copy-Item .env.example .env }
# 编辑 .env，填写自己新建的数据库连接信息和有效配置。已有 .env 时不要覆盖。
```

安装 [uv](https://docs.astral.sh/uv/getting-started/installation/) 后使用 `uv sync --python 3.12 --frozen` 复现锁文件。此命令会调整当前服务的 `.venv`，请先停止使用该环境的进程，或设置 `UV_PROJECT_ENVIRONMENT` 指向新的独立目录。AI 已显式声明 `sqlalchemy[asyncio]`，无需手工补装 greenlet。

AI 从 `customer-service-backend/.env` 加载配置。复制示例后填写模型、LLM 地址、私密 Key、业务 HTTP 地址和独立 AI 数据库 URL；`TODO_` 值必须替换，不可直接运行。两套数据库驱动分别是 `mysql+pymysql` 和 `mysql+aiomysql`。

如果业务中台在虚拟机或另一台机器，使用它实际可访问的地址替换 `COMMERCE_API_BASE_URL`。数字人相关配置当前可不填写，保持文字演示路径。

在 `customer-service-backend` 目录启动：

```powershell
uv run --frozen python -m construction_service.init_db --expected-database ecs_ai
uv run --frozen uvicorn --app-dir construction_service api.app:app --host 127.0.0.1 --port 18082 --no-access-log
```

`--app-dir construction_service` 与当前包布局及内部导入一致，不要省略。`construction_service/main.py` 也包含 Uvicorn 启动代码，但这里使用已验证的显式入口。AI API 文档：<http://127.0.0.1:18082/docs>。

### 5. 安装并启动前端

从项目根目录打开第三个终端：

```powershell
cd .\customer-service-frontend
npm.cmd ci
npm.cmd run dev -- --host 127.0.0.1 --strictPort
```

打开 <http://localhost:5174>。`vite.config.js` 将 `/api`、`/commerce`、`/ws` 转发到本机 `18082`，再由 AI 后端调用业务中台。

构建并预览：

```powershell
npm.cmd run build
npm.cmd run preview -- --host 127.0.0.1 --strictPort
```

开发和预览共用 `5174`，运行预览前停止开发服务器。`--strictPort` 防止端口被占用时悄悄切换，导致代理或隧道指向旧服务。Vite preview 用于演示预览，不代表已完成生产部署。

## 基础用法

### 页面操作

1. 打开前端，自动建立访客 Cookie，无需填写用户 ID 或访问口令。
2. 输入“你好”或“查订单状态”等文字并发送。
3. 选择“发送订单”，客服直接介绍该订单在演示服务中的当前详情。
4. 手机点击顶部“订单 / 商品”打开对象面板，发送后自动回到聊天。
5. 刷新恢复当前历史；点击“新对话”切换到新身份，不删除旧记录。

同一浏览器配置中的多个标签页共享 Cookie，不是独立访客。独立浏览器配置或独立客户端 Cookie 会话才会获得不同身份。

### HTTP 示例

PowerShell 客户端必须先建立访客会话，并在后续请求复用 Cookie：

```powershell
$baseUrl = 'http://127.0.0.1:5174'
Invoke-RestMethod "$baseUrl/api/visitor/session" -SessionVariable visitor

$body = @{ text = '你好' } | ConvertTo-Json
Invoke-RestMethod "$baseUrl/api/chat" -Method Post -WebSession $visitor `
  -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body))

# 从服务实际返回的列表选择订单，不写死不存在的订单号。
$orders = Invoke-RestMethod "$baseUrl/commerce/users/u1001/orders" -WebSession $visitor
if ($orders.data.orders.Count -gt 0) {
  $order = $orders.data.orders[0]
  $body = @{ object = @{ type = 'order'; id = $order.order_id; attributes = @{} } } | ConvertTo-Json -Depth 4
  Invoke-RestMethod "$baseUrl/api/chat" -Method Post -WebSession $visitor `
    -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body))
}

Invoke-RestMethod "$baseUrl/api/chat/history" -WebSession $visitor
Invoke-RestMethod "$baseUrl/api/visitor/session" -Method Post -WebSession $visitor
```

不要通过手工指定 `sender_id` 冒用会话。聊天详情记录是发送时的快照，再次发送订单才会重新查询。业务中台本身存在退款等写接口，但站点演示网关会拒绝它们。

## 项目目录

```text
ecommerce-customer-service/
├── README.md / LICENSE / .gitignore
├── .github/workflows/checks.yml     # 自动检查
├── scripts/                        # 统一检查与提交候选扫描
├── CODEX_HANDOFF.md                 # 早期快照，部分描述已被后续实现更新
├── customer-service-frontend/
│   ├── package.json / package-lock.json
│   ├── index.html / vite.config.js
│   ├── src/
│   │   ├── main.js                  # createApp(App).mount('#app')
│   │   └── App.vue                  # 主界面、会话初始化、消息与对象列表
│   ├── public/images/support-avatar.svg
│   ├── public/digital-human/        # 视频资源，存在不代表当前主流程使用
│   └── vue-demo/                    # 另一个 Vue 示例，非当前网站入口
├── customer-service-backend/
│   ├── pyproject.toml / uv.lock
│   ├── flow_config/                 # system_flows.yml、user_flows.yml
│   ├── check_flows.py / check_steps.py
│   ├── .env.example
│   ├── tests/                      # 访客、访问策略、订单详情、数据库回归
│   └── construction_service/
│       ├── api/                    # FastAPI 装配、路由、签名会话与演示准入
│       ├── config/                 # 环境配置与演示策略
│       ├── domain/                 # 消息、对话状态、业务上下文
│       ├── engine/                 # 对话引擎与装配
│       ├── plan/                   # LLM 规划和结果校验
│       ├── task/                   # 命令、流程、业务 action
│       ├── knowledge/              # 问答与 provider；FAQ/RAG 尚为占位
│       ├── chitchat/ / clarify/    # 闲聊与澄清
│       ├── services/               # 对话服务、业务边界、订单详情
│       ├── repository/ / model/    # AI 对话状态持久化
│       ├── infrastructure/         # DB、HTTP、LLM、数字人客户端
│       ├── prompts/ / history/     # 提示模板与历史构建
│       └── main.py
├── ecommerce-service-backend/
│   ├── pyproject.toml / uv.lock
│   ├── Dockerfile / main.py / .env.example
│   ├── tests/                      # 业务接口与初始化回归
│   └── app/                        # app.py、api.py、config.py、init_demo.py、数据库与模型
└── docs/                           # 实现说明、阶段规划与验收截图
```

本机另有 `backups/`、`.runtime/`、虚拟环境、依赖目录和构建产物，它们不是公共仓库的必要源码。

## 测试与自检

在 `customer-service-backend` 目录执行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -X utf8 check_flows.py
.\.venv\Scripts\python.exe -X utf8 check_steps.py
```

AI 后端的 35 项测试覆盖身份隔离、越权拒绝、演示业务范围、订单详情、数据库字段与日志参数隐藏。业务后端的 7 项测试使用内存 SQLite 覆盖初始化和读取接口，并编译 MySQL DDL；不代表已实测全新 MySQL。前端提供 ESLint 和 3 项 Playwright 浏览器回归，接口使用模拟响应，不调用 LLM 或云服务。

```powershell
# 在主前端目录
npm.cmd run lint
npx.cmd playwright install chromium
npm.cmd test
# 如果浏览器下载失败且已安装 Edge，可选：
# $env:PLAYWRIGHT_CHANNEL = 'msedge'
# npm.cmd test
npm.cmd audit --audit-level=high

# 在业务后端目录
uv run --frozen python -X utf8 -m unittest discover -s tests -v

# 已配置两个 .env，且两个前端（含 vue-demo）均安装依赖后，在根目录统一检查
.\scripts\check.ps1
```

Playwright 使用本机 5175，不占用演示站点 5174。GitHub Actions 定义位于 `.github/workflows/checks.yml`，上传后由 GitHub 执行；本地执行通过不等于远程 CI 已运行。`vue-demo` 是独立遗留示例，使用其自己的 `npm ci`、`npm audit` 和 `npm run build`，主界面测试不覆盖数字人云功能。

## 常见问题

### 启动时报缺少配置或数据库连接失败

检查 AI 的 `.env` 位置、必填 LLM 参数、两套数据库 URL、数据库权限与建表情况。两个服务均加载各自项目根目录 `.env`，进程环境变量优先。启动进程成功也不保证数据库查询成功。

### 找不到 `construction_service`、`api` 或 `app.main`

确认当前目录和命令：AI 使用 `--app-dir construction_service api.app:app`；业务使用 `app.app:app`。根目录空 `main.py`、前端 `vue-demo/` 均不是本网站的启动入口。

### 订单为空、业务网关返回 502 或订单详情失败

检查业务中台、MySQL、`COMMERCE_API_BASE_URL` 和 `u1001` 演示数据。列表范围之外的对象返回 403；无物流记录会明确说明，不会生成虚构轨迹。

### 401 / 403，或新对话后另一个标签页无法发送

先请求 `/api/visitor/session` 并保留 Cookie。新对话会轮换同一浏览器的身份，其他标签页仍持有旧 sender_id 时需刷新。当前口令策略关闭；仅当主动重新启用 `DEMO_ACCESS_REQUIRED` 后才需要口令登录。

### 公网打开提示域名不被允许

`vite.config.js` 的 `allowedHosts` 目前包含本机演示域名，换域名时需更新；隧道目标端口应为 `5174`。没有提供一键隧道安装或部署脚本。公网演示需机器、前后端和业务依赖持续运行，并另外配置 HTTPS；当前 HTTP 不提供传输加密。

### 手机输入时跳动或键盘遮住输入框

刷新加载最新构建。手机布局使用 visualViewport 和 16px 输入字号，避免整页 scrollIntoView；已验证缩小视口，但 iPhone 微信真实键盘仍需实机确认。参考 [手机布局修复说明](docs/手机聊天布局修复.md)。

### 数字人不可用 / 构建提示大包

文字演示无需启动数字人。后端云 SDK、云资源和音视频实测仍待配置；前端 SDK 按需加载，构建时存在大 chunk 提示，不是文字聊天构建失败。不要为演示文字路径擅自申请云资源。

### 能否直接执行 `docker compose up`？

不能：当前没有 Compose 文件。业务子项目文档已同步真实入口。Dockerfile 只涵盖业务后端，不自动提供数据库、演示数据、AI 服务或前端；需通过环境变量传入私密配置。

## 贡献指南

1. 通过本仓库的 Issue / Pull Request 提交问题和改动，目标分支为 `main`。TODO：完善维护者分工和模板。
2. 修改前阅读调用链；遵循现有模块边界，AI 只能通过 HTTP 查询电商业务数据。
3. 控制修改范围，不覆盖现有数据或本机配置。新增功能要明确成功、空数据、异常和权限行为。
4. 后端改动运行相关回归与流程自检；前端改动构建并检查桌面/手机。PR 写明问题、行为变化、验证结果和剩余限制。
5. 不提交 `.env`、密钥、口令、运行日志、数据库导出、`backups/`、`.venv/`、`node_modules/`、`dist/` 或编辑器缓存。仓库已提供 `.gitignore` 和两套 `.env.example`。发布前执行 `python scripts/check_repository.py` 检查候选清单；它不会输出命中的凭据值。

访客签名密钥保存在用户应用数据目录的 `ecommerce-customer-service/visitor-session.key`，Windows 下位于 `%LOCALAPPDATA%`；不要上传。源码配置文件存在历史凭据注释，发布前必须脱敏并确认凭据轮换；README 不复述这些值。

## 许可证与发布限制

根 [LICENSE](LICENSE) 当前明确未授予开源或再发布许可，只用于说明私有准备状态。**TODO：核实原教学代码、图片和视频授权，确认署名后再选择开源许可证。** 第三方依赖仍适用各自许可证。

本机私密配置、备份和缓存被 `.gitignore` 排除，但保留在电脑上。不要直接打包整个工作目录上传；已经泄露或曾被分享的 API Key、数据库口令必须在账号侧轮换，删除源码值不能使旧凭据失效。仓库保持 private；公开前仍需确认授权。

功能未完成项与验收条件见 [功能边界与后续计划](docs/功能边界与后续计划.md)。
