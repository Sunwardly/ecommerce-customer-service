# 电商智能客服（电商小二二次开发）· Codex 二次开发交接文档

> **文档版本**：v1.0 · **快照日期**：2026-10-08 · **对应工作区状态**：非 git 仓库（未 `git init`）
>
> 本文是**某个时点的快照**，用于让 Codex 快速接手并安全地进行功能扩展。
> 接续工作前请先按 §0 核对代码是否有新变动。

---

## 0. 30 秒上手（Codex 第一轮必读）

```bash
cd D:/QWER/Projects/ecommerce-customer-service
export PATH="/usr/bin:/bin:$PATH"   # ⚠️ 本机 Bash 偶发丢 /usr/bin，报错先加这句

# 1. 先读这三份（顺序不能颠倒）
#    - CODEX_HANDOFF.md          ← 本文，全局上下文
#    - docs/电商小二二次开发阶段规划.md  ← 现状盘点 + 九阶段路线
#    - customer-service-backend/construction_service/api/app.py  ← 应用装配入口
```

**一句话现状**：文字对话主链路（task / knowledge / chitchat 三轨道）**已跑通**，但知识检索是占位实现、
无测试、无鉴权、非 git 仓库。当前定位是**教学项目的二次开发底座**，不是可上线产品。

**改代码前务必知道的三件事**：
1. 这是**非 git 仓库**——**没有版本回滚能力**，任何改动都可能不可逆。改前先手工备份或先 `git init`。
2. **源码里有明文 API Key**（见 §7.1），任何 `git init` + `push` 之前必须先处理。
3. AI 后端**禁止直连业务数据库**——这是全项目第一号架构约束（见 §7.2）。

---

## 1. 项目背景与目标

| 项 | 值 |
| --- | --- |
| 项目定位 | 电商场景多轮对话智能客服系统；教学项目"电商小二"的二次开发版本 |
| 仓库根 | `D:\QWER\Projects\ecommerce-customer-service` |
| 形态 | 三仓库单根目录（前端 + AI 后端 + 模拟业务中台），**非 monorepo 工具管理**，仅物理同目录 |
| 角色与周期 | [ 待补充：你的角色，如"独立负责后端" ] · [ 待补充：起止时间 ] |
| 原教学项目 | 参考仓库 `github.com/2019hzk/260119-ecommerce-customer` |
| 教学资料 | `D:\桌面\资料文档\sgg\电商小二资料`（day01 / day02 / 设计文档 03–14 / 面试指南） |
| 远期目标 | 改造为自有产品，承载自有业务（见 `docs/电商小二二次开发阶段规划.md` 第四部分） |

### 核心设计主线（五条，改代码时的判断依据）

1. **三轨道互斥，由 LLM 路由** —— 一轮对话只走 task / knowledge / chitchat 之一
2. **永不裸用 LLM 输出** —— 结构化输出 → 白名单校验 → 失败走澄清兜底
3. **YAML 描述流程，代码执行流程** —— 可枚举的步骤交给状态机，不可枚举的才交给 LLM
4. **状态集中、计算集中、IO 集中** —— 状态一份内存对象承载；引擎无副作用；读写只发生在 Service 层
5. **业务隔离** —— AI 后端只是业务系统的消费者，不直连业务库

---

## 2. 技术栈及依赖版本

### 2.1 AI 后端（`customer-service-backend`）

| 项 | 值 |
| --- | --- |
| 语言 | Python **3.13.13**（`pyproject.toml` 要求 `>=3.12`） |
| 虚拟环境 | `.venv`（`D:\miniconda\python.exe -m venv` 手工创建，**非 uv 管理**） |
| Web 框架 | FastAPI **0.136.1** · Uvicorn **0.47.0**（`[standard]`） |
| LLM 编排 | LangChain **1.3.1** · langchain-openai **1.1.14+** · openai **2.37.0** |
| 配置 | pydantic-settings **2.13.1+** · pydantic **2.13.4** |
| 持久化 | SQLAlchemy **2.0.49** · aiomysql **0.3.2** · PyMySQL **1.1.3** · cryptography |
| 模板 | Jinja2 **3.1.6** · PyYAML **6.0.3** |
| HTTP 客户端 | httpx **0.28.1** |
| 数字人 SDK | 阿里云灵眸 `lm-avatar-chat-sdk`（前端依赖；后端 SDK **当前未安装**，功能自动降级） |
| 入口 | `construction_service/main.py` → `uvicorn api.app:app` |

> ⚠️ `uv.lock` **存在但与 `.venv` 已脱节**——实际环境是手工 venv，`construction_service` 未安装进 site-packages。
> 不要假设 `uv sync` 能还原出可用环境。

### 2.2 业务中台（`ecommerce-service-backend`）

| 项 | 值 |
| --- | --- |
| 语言 | Python **>=3.11,<3.13**（**与 AI 后端版本要求冲突，不能共用同一虚拟环境**） |
| Web 框架 | FastAPI `>=0.135.3` · Uvicorn |
| ORM | SQLAlchemy **2.0.38+** · PyMySQL（**同步**驱动） |
| 数据库 | MySQL **8.x**（虚拟机 `192.168.200.120:3306`，库名 `commerce`） |
| 配置 | 纯 `os.getenv` + dataclass（**未加载 dotenv，`.env` 实际不生效**，见 §7.1） |
| 部署 | 有 `Dockerfile`（基于 `python:3.11-slim`，uv 管理依赖），无 compose 文件 |

### 2.3 前端（`customer-service-frontend`）

| 项 | 值 |
| --- | --- |
| 框架 | Vue **3.5.13** · Vite **6.2.0** · `@vitejs/plugin-vue` 5.2.1 |
| 实际端口 | **5174**（dev 与 preview 共用；教学文档写的 5173 **是错的**） |
| 结构 | **单文件组件**：`src/App.vue` 约 3064 行（template + script + style 全在一个文件） |
| 依赖 | 仅 `vue` + `lm-avatar-chat-sdk`；**无路由库、无状态管理库、无 TypeScript、无 ESLint/Vitest** |
| 代理 | `vite.config.js` 内硬编码（`/api` → 18082、`/commerce` → 18081、`/ws` → 18082） |
| 环境配置 | **无 `.env` 文件**，所有后端地址写死在构建配置里 |

### 2.4 外部依赖全景

| 依赖 | 地址 / 值 | 用途 |
| --- | --- | --- |
| MySQL（业务库） | `192.168.200.120:3306` / 库 `commerce` / 账号 `qxl123`（**密码见 `.env`**） | 业务中台数据 |
| MySQL（状态库） | `192.168.200.120:3306` / 库 `customer_service` / 账号 `root`（**密码见 `.env`**） | 对话状态单表 |
| LLM 服务 | `https://api.deepseek.com` · 模型 `deepseek-v4-flash` | 规划 / 澄清 / 改写 / 知识 / 闲聊共 5 处调用 |
| 阿里云灵眸 | `lingmou.cn-beijing.aliyuncs.com` | 数字人云渲染（当前未启用） |
| 花生壳内网穿透 | `12lh9932zk192.vicp.fun` | 对外演示 |

---

## 3. 目录结构与核心模块职责

### 3.1 总体结构

```
ecommerce-customer-service/
├── CODEX_HANDOFF.md                    ← 本文
├── main.py                             ← ⚠️ 空文件（0 字节），疑似残留，无实际用途
├── docs/
│   └── 电商小二二次开发阶段规划.md        ← 现状盘点 + 九阶段路线（重要）
├── customer-service-backend/           ← AI 对话后端（18082），主战场
│   ├── .env                            ← ⚠️ 含明文密钥，未 gitignore
│   ├── .venv/                          ← 手工 venv（3.13.13）
│   ├── pyproject.toml / uv.lock        ← ⚠️ 声明与实际环境已脱节
│   ├── check_flows.py / check_steps.py ← 手工自检脚本（非 pytest）
│   ├── flow_config/
│   │   ├── user_flows.yml              ← 业务 6 流程定义（YAML）
│   │   └── system_flows.yml            ← 系统 6 流程定义（YAML）
│   └── construction_service/           ← 自有代码包（注意：所有 import 用这个前缀）
│       ├── main.py                     ← 启动入口
│       ├── api/                        ← 路由层
│       ├── services/                   ← 事务边界（唯一 IO 发生地）
│       ├── engine/                     ← 顶层调度
│       ├── plan/                       ← LLM 规划 + 校验
│       ├── clarify/                    ← 澄清兜底
│       ├── task/                       ← task 轨道
│       ├── knowledge/                  ← knowledge 轨道
│       ├── chitchat/                   ← chitchat 轨道
│       ├── domain/                     ← 领域模型（状态 / 上下文 / 消息）
│       ├── model/                      ← ORM 映射
│       ├── repository/                 ← 持久化
│       ├── infrastructure/             ← LLM / HTTP / DB / 数字人客户端
│       ├── config/                     ← 配置（⚠️ 含明文密钥）
│       ├── prompts/jinja2/             ← 4 个提示词模板
│       └── history/                    ← 历史对话组装
├── ecommerce-service-backend/          ← 模拟电商业务中台（18081）
│   ├── main.py / app/                  ← 应用代码
│   ├── Dockerfile / .dockerignore      ← 唯一容器化配置
│   └── README.md                       ← 业务中台说明
└── customer-service-frontend/          ← 可视化控制台（5174）
    ├── vite.config.js                  ← ⚠️ 后端地址硬编码在此
    └── src/
        ├── App.vue                     ← 3064 行单文件组件（前端全部逻辑）
        ├── main.js
        └── assets/logo.webp
```

### 3.2 AI 后端分层调用链

```
api（路由）                        api/router/chat_router.py
  │                                api/router/avatar_router.py      （数字人 HTTP）
  │                                api/router/avatar_ws_router.py   （数字人 WebSocket）
  ↓
service（事务边界：读状态/存状态）    services/dialogue_service.py
  ↓
engine（顶层调度，纯计算）           engine/dialogue_engine.py
  ├─ plan（LLM 规划）               plan/planner.py + prompts/jinja2/turn_plan.jinja2
  ├─ validator（白名单校验）          plan/validator.py
  ├─ clarify（澄清兜底）             clarify/responder.py
  └─ 三轨道之一（互斥）：
       task       task/handler.py → task/command/processor.py
                                     → task/flow/executor.py → task/action/runner.py
       knowledge  knowledge/handler.py → knowledge/providers/registry.py
                                     → knowledge/responder.py
       chitchat   chitchat/handler.py → chitchat/responder.py
  ↓
domain（领域模型） / repository（持久化） / infrastructure（LLM、HTTP、DB）
```

### 3.3 核心模块职责速查表

| 模块 / 文件 | 职责 | 是否通用层（换业务基本不改） |
| --- | --- | --- |
| `api/router/chat_router.py` | 对话 HTTP 入口（`POST /api/chat`、`GET /api/chat/history`） | ✅ 通用 |
| `api/schemas.py` | 接口层数据模型（请求 / 响应）与领域模型互转 | ✅ 通用 |
| `api/app.py` | FastAPI 应用装配 + `lifespan` 启动初始化 | ✅ 通用 |
| `api/dependencies.py` | 引擎单例装配与依赖注入 | ⚠️ 半通用（装配新 Provider 时要改） |
| `services/dialogue_service.py` | **唯一事务边界**：加载状态 → 调引擎 → 保存状态 | ✅ 通用 |
| `engine/dialogue_engine.py` | 顶层调度：判消息类型 → 调规划 → 校验 → 分派轨道 | ⚠️ 半通用（含硬编码对象映射） |
| `engine/builder.py` | 引擎构建 | ✅ 通用 |
| `plan/planner.py` | 调 LLM 产出结构化 `TurnPlan` | ✅ 通用 |
| `plan/validator.py` | 意图 / 流程 / 槽位白名单校验 | ⚠️ 校验口径属契约（见 §7.1 缺陷 2） |
| `plan/turn_plan.py` | 规划结果数据模型 | ✅ 通用（有一处拼写 bug） |
| `clarify/responder.py` | 澄清提问生成 | ✅ 通用（话术需按业务改写） |
| `domain/state.py` | `DialogueState` 聚合根 / `Session` / `Turn` / `FocusedObject` | ✅ 通用（有一处序列化 bug） |
| `domain/contexts.py` | `TaskContext` / `SystemContext` 及子类 | ✅ 通用 |
| `domain/messages.py` | `UserMessage` / `BotMessage` / `MessageType` | ✅ 通用 |
| `task/handler.py` | task 轨道入口（两阶段协调者） | ✅ 通用 |
| `task/command/processor.py` | 4 种命令：开启 / 取消 / 恢复 / 填槽 | ✅ 通用 |
| `task/flow/executor.py` | 流程执行器：外层/内层循环、4 种步骤 | ⚠️ **含硬编码对象映射（缺陷 3）** |
| `task/flow/{flows,steps,links,loader}.py` | YAML 流程数据模型与加载 | ✅ 通用 |
| `task/action/{base,runner,builder,register}.py` | 动作框架 + 自动扫描注册 | ✅ 通用 |
| `task/action/builtin/*` | 内置动作（响应、监听） | ✅ 通用 |
| `task/action/customer/*` | **业务动作**（查物流 / 查订单 / 推荐商品） | ❌ **换业务必改** |
| `task/action/customer/shared.py` | 业务动作共享工具 | ❌ 换业务必改 |
| `knowledge/handler.py` | knowledge 轨道入口 | ✅ 通用 |
| `knowledge/intents.py` | **知识意图注册表**（7 个意图 ↔ Provider） | ❌ **换业务必改** |
| `knowledge/providers/registry.py` | Provider 注册表 | ✅ 通用 |
| `knowledge/providers/knowledge.py` | 4 个 Provider 实现（2 真实 + 2 占位） | ❌ 换业务必改 |
| `knowledge/providers/base.py` | `KnowledgeProvider` / `KnowledgeChunk` 契约 | ⚠️ **契约需扩充（缺 score/source）** |
| `knowledge/responder.py` | 上下文拼接 + 交给 LLM 生成 | ✅ 通用 |
| `chitchat/*` | 闲聊轨道 | ✅ 通用 |
| `repository/dialogue_repository.py` | 状态单表 upsert（⚠️ MySQL 方言） | ✅ 通用 |
| `model/state_record.py` | ORM 映射 `dialogue_states(sender_id, state_json)` | ✅ 通用 |
| `infrastructure/llm_client.py` | LLM 客户端（5 处调用共用） | ✅ 通用 |
| `infrastructure/db.py` | 异步 MySQL 引擎 | ✅ 通用 |
| `infrastructure/http_client.py` | httpx 客户端（120s 超时、忽略代理） | ✅ 通用 |
| `infrastructure/avatar.py` | 数字人会话客户端（⚠️ 进程级单例） | ⚠️ 按需 |
| `config/settings.py` | 配置类（⚠️ docstring 含明文密钥） | ⚠️ |
| `prompts/jinja2/*.jinja2` | 4 个提示词模板 | ❌ **换业务必改** |
| `flow_config/*.yml` | 12 条流程定义 | ❌ **换业务必改** |

### 3.4 业务中台模块

| 文件 | 职责 |
| --- | --- |
| `app/app.py` | FastAPI 应用装配 |
| `app/api.py` | 9 个业务接口（见 §5.1） |
| `app/models.py` | 8 张表 ORM 映射 |
| `app/schemas.py` | 接口数据模型 |
| `app/database.py` | 同步 SQLAlchemy 引擎 + Session |
| `app/config.py` | 配置（⚠️ `.env` 不生效） |

---

## 4. 本地环境搭建与启动 / 构建 / 测试命令

### 4.1 环境搭建

**前置条件**

| 项 | 要求 | 检查命令 |
| --- | --- | --- |
| MySQL | **已建好库和表**（本仓库**无建表脚本**，见 §7.1） | `mysql -h 192.168.200.120 -u qxl123 -p -e "use commerce; show tables;"`（密码见 `.env`） |
| Python | 3.12+ 用于 AI 后端；3.11/3.12 用于业务中台 | `python --version` |
| Node.js | 18+ | `node --version` |

> ⚠️ **两个后端的 Python 版本要求互相冲突**（AI 后端 `>=3.12`，业务中台 `>=3.11,<3.13`）。
> 不要试图共用一个虚拟环境。

**AI 后端的虚拟环境（若不存在需重建）**

```bash
cd customer-service-backend
D:/miniconda/python.exe -m venv .venv
.venv/Scripts/python.exe -m pip install -i https://mirrors.aliyun.com/pypi/simple/ \
    fastapi uvicorn[standard] langchain langchain-openai pydantic-settings \
    sqlalchemy aiomysql pymysql cryptography jinja2 pyyaml httpx
```

**前端依赖**

```bash
cd customer-service-frontend && npm install
```

### 4.2 启动（**必须按此顺序**）

```bash
export PATH="/usr/bin:/bin:$PATH"
```

**① 虚拟机上启动 MySQL（前提，本仓库不负责）**
→ 确认 `192.168.200.120:3306` 可达、`commerce` 与 `customer_service` 两库的**表已存在**。

**② 业务中台（18081）** —— 必须在自己的目录里跑（用的是相对导入 `app.app:app`）

```bash
cd ecommerce-service-backend
uv run uvicorn app.app:app --host 0.0.0.0 --port 18081
# 或（无 uv 时）
python -m uvicorn app.app:app --host 0.0.0.0 --port 18081
```

自检：`curl http://127.0.0.1:18081/health` → 应返回 `{"data":{"status":"ok"}}`

**③ AI 后端（18082）** —— ⚠️ **`--app-dir` 不是多余的**（见下方说明）

```bash
cd customer-service-backend
.venv/Scripts/python.exe -m uvicorn --app-dir construction_service api.app:app --host 0.0.0.0 --port 18082
```

> **为什么必须加 `--app-dir construction_service`？**
> `main.py` 里写的是 `api.app:app`（相对子包路径），但代码里所有 import 都是 `construction_service.*`
> （要求 `customer-service-backend/` 在后端根在 `sys.path`）。**两个要求方向相反**，实测三种情况：
>
> | 方式 | `construction_service` | `api.app` | 结果 |
> | --- | --- | --- | --- |
> | `cd customer-service-backend` 直接跑 | ✅ 可导入 | ❌ 解析失败 | 失败 |
> | `cd construction_service` 跑 | ❌ 导入失败 | ✅ 可解析 | 失败 |
> | 加 `--app-dir construction_service` | ✅ | ✅ | **成功** |
>
> PyCharm 里能右键直接跑，是因为 IDE 勾了 "Add source roots to PYTHONPATH" 替你补上了。

自检：

```bash
curl http://127.0.0.1:18082/hello
# → {"success":"ok"}
curl "http://127.0.0.1:18082/api/chat/history?sender_id=diag_probe"
# → {"sender_id":"diag_probe","messages":[]}
```

**④ 前端（5174）**

```bash
cd customer-service-frontend && npm run dev      # 开发
# 或
npm run build && npm run preview                 # 演示（端口同为 5174）
```

打开 `http://127.0.0.1:5174`

### 4.3 构建

| 目标 | 命令 |
| --- | --- |
| AI 后端 | 无构建步骤（Python 直跑） |
| 业务中台 Docker 镜像 | `cd ecommerce-service-backend && docker build -t ecommerce-app:latest .`（需可访问 `docker.1ms.run` 镜像源） |
| 前端生产构建 | `cd customer-service-frontend && npm run build` → 产物在 `dist/` |

### 4.4 测试

> ⚠️ **本仓库没有任何自动化测试。** 全仓无 `tests/` 目录、无 pytest、无 Vitest、无 CI 配置。
> 目前只有两个手工自检脚本（非测试框架）：

```bash
cd customer-service-backend
.venv/Scripts/python.exe check_flows.py    # 检查 YAML 流程定义完整性
.venv/Scripts/python.exe check_steps.py    # 检查流程步骤引用有效性
```

**Codex 新增功能时，建议同步补测试**——这是当前最大的工程化缺口（见 §8）。

---

## 5. 关键数据流与外部接口

### 5.1 AI 后端暴露的接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/chat` | **对话主入口**（文本消息 / 对象消息） |
| `GET` | `/api/chat/history` | 查询历史对话（`?sender_id=`） |
| `GET` | `/hello` | 健康检查 |
| `GET` | `/api/avatar/session` | 创建数字人云渲染会话 |
| `DELETE` | `/api/avatar/session` | 释放数字人会话 |
| `WS` | `/ws/avatar/chat` | 数字人对话 WebSocket |
| `GET` | `/docs` | OpenAPI 文档 |

### 5.2 业务中台暴露的接口（AI 后端的消费对象）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/health` | 健康检查（含 DB 连通性） |
| `GET` | `/users/{user_id}/orders` | 用户最近订单列表（默认 5 条） |
| `GET` | `/users/{user_id}/products` | 用户最近购买商品（默认 5 条，去重） |
| `GET` | `/orders/{order_id}` | 订单详情（含收货信息 + 商品明细） |
| `GET` | `/orders/{order_id}/status` | 订单状态 |
| `GET` | `/orders/{order_id}/logistics` | 物流信息（含轨迹，按时间倒序） |
| `GET` | `/products/{product_id}` | 商品详情 |
| `POST` | `/orders/{order_id}/shipping-reminders` | **写操作**：创建发货提醒（限"待发货/待揽收"） |
| `POST` | `/orders/{order_id}/refund-applications` | **写操作**：创建退款申请（已有进行中申请则 409） |

**统一响应包装**：`{"data": {...}}`；错误为标准 `HTTPException(detail=...)`。

### 5.3 主数据流：一条文本消息的完整走向

```
① 前端 POST /api/chat  {sender_id, message:{type:"text", text:"..."}}
        │
② chat_router.py          接口模型 → 领域模型（UserMessage）
        │
③ dialogue_service.py     ┌─ 读状态（IO #1）
                          │   repository → model/state_record.py → MySQL.customer_service
                          │   （load 后判 60 分钟会话超时，超时则重建 Session）
        │                 └─ 交给 engine
④ dialogue_engine.py      按 message.type 分流：
                          "text" → _hand_text_msg（三轨道）
                          "object" → _hand_obj_msg（仅 task 轨道填槽/设聚焦对象，**不进知识轨道**）
        │
⑤ plan/planner.py         LLM 调用 #1：喂 [用户消息 + 历史 turns[-10:] + 可选意图/流程清单]
                          → 结构化 TurnPlan（标注走哪条轨道）
        │
⑥ plan/validator.py       白名单校验：
                          意图是否注册 / 流程是否存在 / requires_object 与 focused_object 是否匹配
                          ├─ 不通过 → ⑦ clarify/responder.py（LLM 调用 #2）→ 返回澄清问题
                          └─ 通过   → ⑧ 三轨道之一
        │
⑧a task 轨道    handler → command/processor（4 命令）→ flow/executor（推进流程）
                          → action/runner（执行动作）
                          → 业务动作内部 httpx 调业务中台 18081（AI 唯一允许的数据获取方式）
⑧b knowledge 轨道  handler → 意图展开为 provider_ids → 逐个 retrieve()
                          → responder 拼上下文（"\n\n".join）→ LLM 调用 #3 生成
⑧c chitchat 轨道   handler → responder → LLM 调用 #4 生成
        │
⑨ dialogue_service.py     └─ 写状态（IO #2）：repository upsert → MySQL
        │
⑩ 返回 BotMessage 列表 → 前端渲染（文本 + 可选对象卡片）
```

**核心事实：整条链路只有 2 次数据库 IO**（步骤 ③ 读、⑨ 写），中间全是内存对象计算。
这是分层设计最核心的一条，改动时**不要把 IO 泄漏到 engine 层**。

### 5.4 状态持久化

| 项 | 内容 |
| --- | --- |
| 表 | `dialogue_states` |
| 结构 | `sender_id` (PK, varchar) + `state_json` (TEXT) |
| 内容 | 整个 `DialogueState` 序列化为一个 JSON 字符串 |
| 写入 | upsert（MySQL 方言 `on_duplicate_key_update`） |
| 会话超时 | 60 分钟（硬编码在 `dialogue_engine.py`） |
| ⚠️ 已知问题 | `Session.to_dict()` 把 `last_activity_at` 误写进 `closed_at` 字段（见 §7.1 缺陷 4） |

### 5.5 第三方服务

| 服务 | 用途 | 当前状态 |
| --- | --- | --- |
| DeepSeek API | 5 处 LLM 调用（规划 / 澄清 / 知识 / 闲聊 / 回话改写） | ✅ 可用（Key 在 `.env`） |
| 阿里云灵眸 | 数字人云渲染 | ⚠️ SDK 未安装，功能降级为返回空对象 |
| 花生壳内网穿透 | 对外演示 | ✅ 已注册域名 |

---

## 6. 编码规范与提交约定

### 6.1 编码规范（从现有代码归纳）

> ⚠️ 本仓库**没有配置任何 linter / formatter**（无 ruff、无 black、无 mypy 配置、无 ESLint）。
> 以下是从现有代码风格归纳的约定，**新增代码应当保持一致**。

**Python**

| 约定 | 示例 |
| --- | --- |
| 所有 import 用完整包名前缀 | `from construction_service.domain.state import DialogueState` |
| 领域模型用 `@dataclass` | `@dataclass(slots=True) class Session:` |
| 需要静态类型提示的 ORM 用 `Mapped` / `mapped_column` | `sender_id: Mapped[str] = mapped_column(primary_key=True)` |
| 中文注释为主，行内解释"为什么"而非"是什么" | 见 `model/state_record.py` |
| 异步优先（路由、Provider、IO 全 `async def`） | — |
| 配置集中在 `config/settings.py`（Pydantic Settings） | 不要散落 `os.getenv` |

**前端**

| 约定 | 说明 |
| --- | --- |
| 单文件组件（`App.vue`） | 现状如此，**产品化改造时再拆分**（见规划阶段 5） |
| `ref` + `computed`（Composition API） | 无 Pinia / Vuex |
| `senderId` 作为用户标识贯穿所有请求 | ⚠️ 当前默认值 `'u1001'` 是硬编码假值 |

### 6.2 提交约定

> ⚠️ **本目录当前不是 git 仓库**（`git rev-parse` 返回 `fatal: not a git repository`），
> **没有 `.gitignore`**，也没有任何提交历史可参照。

**Codex 若要建立版本控制，必须按以下顺序：**

```
1. 先补 .gitignore（必须包含 .venv/、node_modules/、__pycache__/、*.pyc、.env、.idea/、dist/）
2. 再把 config/settings.py docstring 里的明文密钥删掉（§7.1 缺陷 1）
3. 然后才 git init + 首次提交
4. 确认 .env 未被纳入（git status 检查）
```

**建议的提交信息格式**（参考原教学项目）：`<类型>: <简短描述>`，类型用 `feat` / `fix` / `refactor` / `docs` / `chore`。

### 6.3 单次改动规模约定

- **一次只改一件事**：流程 YAML 的改动与框架代码的改动**不要混在一次提交里**
- 改提示词（`prompts/jinja2/*.jinja2`）后**必须手工跑一遍三条轨道**验证（当前无回归测试可依赖）
- 改 `flow_config/*.yml` 后**必须**跑 `check_flows.py` + `check_steps.py`

---

## 7. 已知问题与技术债务

### 7.1 缺陷清单（按严重度排序，附代码级证据）

| # | 缺陷 | 证据位置 | 影响 | 优先级 |
| --- | --- | --- | --- | --- |
| 1 | **真实 API Key 落在源码里** | `config/settings.py` 的 **docstring** 里明文写了 `LLM_API_KEY=sk-...`；`customer-service-backend/.env` 也含真实 key。仓库**无 `.gitignore`、未 git init** | 一旦提交进公开仓库即泄露，可被盗刷 | **P0 · 立刻** |
| 2 | **白名单校验不白名单** | `plan/validator.py:110` 直接 `intents[intent]` 取字典。LLM 编造未注册意图 id 时抛 `KeyError` → 500，**而不是走澄清兜底** | 直接打在"防幻觉"卖点上：幻觉把请求打崩而非被拦下 | **P0** |
| 3 | **对象卡片→槽位映射硬编码在三处** | ① `task/flow/executor.py:245-251` 写死 `order → order_number` / `product → product_id` ② `engine/dialogue_engine.py` 同样写死 ③ 前端 `App.vue` 模板写死 `'order' / 'product'` | 换业务**必须改三层代码**，不能靠配置 | **P1** |
| 4 | **会话关闭时间序列化错误** | `domain/state.py:` `Session.to_dict()` 里 `"closed_at": self.last_activity_at` —— 把最后活跃时间写进了关闭时间字段 | 会话是否已关闭在存取一轮后失真 | **P1** |
| 5 | **数字人会话是进程级单例** | `infrastructure/avatar.py` 用模块级 `_session`，注释自认"当前进程复用同一个数字人会话" | 多用户互相串台 | P1 |
| 6 | **业务中台 `.env` 是死配置** | `app/config.py` 只用 `os.getenv`，**未调用 `load_dotenv`**。`.env` 文件存在但从不被读取，实际生效的是代码里的默认值 | 改 `.env` 不生效，排查时极易误判 | **P1** |
| 7 | **无任何身份体系 / 鉴权** | 6 个路由入口无一处鉴权；`sender_id` 由客户端自报；前端默认 `'u1001'` | 任意人可读任意用户历史 | P1 |
| 8 | **回复的 `sender_id` 是硬编码假值** | `engine/dialogue_engine.py:78` 返回 `ProcessResult(sender_id="1001", message_id="11111")` | 与真实用户无关 | P1 |
| 9 | **知识检索是占位实现** | `knowledge/providers/knowledge.py`：`FAQProvider.retrieve()` 固定返回"未检索到相关问题"；`RAGProvider.retrieve()` 同样返回占位文本 + TODO | 5/7 个知识意图喂给 LLM 的永远是占位内容 | P1 |
| 10 | **`KnowledgeChunk` 契约不完整** | `knowledge/providers/base.py:6-8` 只有 `content` 字段，**无 `score` / `source` / `doc_id`** | 接入真向量检索后无法排序、无法设阈值、无法给出处 | P1（接 RAG 前必须修） |
| 11 | **无活动任务时取消会崩** | `task/command/processor.py:_process_cancel_flow` 直接取 `active_task.flow_id`，未判空 | LLM 在无流程时输出 `cancel_flow` 即异常 | P2 |
| 12 | **找不到边时返回伪 step_id** | `flow/executor.py:_select_step_id` 无匹配时返回字符串 `"not exist  link"` 当步骤 ID | 隐蔽失败，异常点远离病因 | P2 |
| 13 | **持久化锁死 MySQL 方言** | `repository/dialogue_repository.py` 用 `on_duplicate_key_update` | 换库需重写 | P2 |
| 14 | **`TurnPlan.activated_tracks()` 拼写错误** | `plan/turn_plan.py` 返回 `"chichat"`（少一个 t），与 validator 比较字符串不一致 | 目前恰好无害，是定时炸弹 | P2 |
| 15 | **配置硬编码在代码里** | 会话超时 `60*60` 在 `dialogue_engine.py`；LLM `timeout=120`、`temperature=0` 在 `infrastructure/llm_client.py` | 调参要改代码 | P2 |
| 16 | **数据库 echo 常开** | `infrastructure/db.py` 固定 `echo=True` | 生产环境打印全部 SQL，可能把对话内容写进日志 | P2 |
| 17 | **前端调用不存在的接口** | `App.vue:929` 调 `POST /api/avatar/sessions/cleanup`，后端只有 `GET/DELETE /api/avatar/session`（单数，无 `/cleanup`） | 被 try/catch 静默吞掉，无效代码 | P3 |
| 18 | **前端后端地址硬编码在构建配置** | `vite.config.js` 写死 `127.0.0.1:18082`、`192.168.200.120:18081`、花生壳域名、端口 5174 | 无法分离开发/演示/生产环境 | P3 |
| 19 | **根目录 `main.py` 是空文件** | `D:\...\ecommerce-customer-service\main.py`（0 字节） | 疑似残留，无用途 | P3 |
| 20 | **`uv.lock` 与实际环境脱节** | `.venv` 是手工 venv（3.13.13），`construction_service` 未装进 site-packages，但 `uv.lock` 存在 | 不要假设 `uv sync` 能还原环境 | P3 |

### 7.2 功能性缺口（不是 bug，是"还没做"）

| 缺口 | 现状 |
| --- | --- |
| **无建表脚本** | 全仓无 `create_all`、无 `CREATE TABLE`、无 `initdb` 目录。`dialogue_states` 与 commerce 的 8 张表**必须在虚拟机 MySQL 里已存在**，否则第一次发消息报错 |
| 商品推荐是空壳 | `task/action/customer/recommend_similar_products.py` 只回一句"当前版本还没有接入正式的推荐系统" |
| 人工客服不成立 | `human_handoff` 流程只回一句"正在转接"，无坐席端、无工单、无排队 |
| 无流式输出 | 全部整段返回，无打字机效果 |
| 无测试 / 无 CI | 全仓无测试目录，无 `.gitlab-ci.yml` / `.github/` |
| 无可观测性 | 5 处 LLM 调用共用一个客户端，**无调用量、延迟、token 花费、澄清率记录** |
| 状态只能整体读写 | 单表 JSON，历史分析需自己拆 JSON |

### 7.3 环境类坑（排查时先看这里）

| 现象 | 真因 | 对策 |
| --- | --- | --- |
| `construction_service` 导入失败 / `api.app` 解析失败 | cwd 与 sys.path 要求冲突 | 必须加 `--app-dir construction_service` |
| cmd 里 `.venv/Scripts/python.exe` 报"不是内部命令" | **cmd 把 `/` 当参数开关**，读成"命令 `.venv` + 参数 `/Scripts/python.exe`" | 用反斜杠 `.venv\Scripts\python.exe`，且**必须一行写完**（cmd 不认 `\` 续行） |
| 数字人功能不生效 | 阿里云灵眸 SDK 未安装，`LINGMOU_AVAILABLE=False` | 属预期降级，`/api/avatar/session` 返回空对象 |
| Bash 里 `head` / `grep` / `dirname` 报 command not found | 本机 Bash 偶发丢 `/usr/bin` | 命令前加 `export PATH="/usr/bin:/bin:$PATH"` |

---

## 8. 后续迭代计划

完整路线见 `docs/电商小二二次开发阶段规划.md`（九个阶段）。**摘要如下：**

```
阶段 0 基线复现  →  1 业务边界  →  2 契约设计  →  3 数据底座  →  4 对话配置  →  5 界面产品化
                                                                              ↓
                                                    8 交付上线  ←  7 质量可观测  ←  6 业务闭环
```

| 阶段 | 核心目标 | 关键交付物 |
| --- | --- | --- |
| **0 基线复现** | 独立跑通三件套，三条轨道各打通一条 | 可复现启动清单 · 文件分类表 · **补 `.gitignore` + 移除明文密钥（不排队，立刻做）** |
| **1 业务边界** | 确定新业务做什么（只写文档） | 意图盘点表（问题 → 归类 → 路径 → 依赖系统）· 术语命名表 |
| **2 契约设计** | 把意图翻译成可执行契约 | 接口契约 · 对象 schema · **三向映射表（槽位↔对象字段↔接口字段）** · 校验口径定义 |
| **3 数据底座** | 契约变成能跑的接口 + 种子数据 | 建表脚本 · 接口实现 · 种子数据（正常+边界+异常） |
| **4 对话内容适配** | 换业务主战场（尽量不动框架） | 新流程 YAML · 槽位 · 知识意图接法 · 提示词 · 兜底话术 |
| **5 界面产品化** | 3064 行单文件组件 → 可用的界面 | 界面拆分 · 卡片交互 · 异常态表达 · 配置外置 |
| **6 业务闭环** | 从"AI 自己玩"到"业务能跑" | 身份与会话归属 · 权限边界 · 人工接管通道 |
| **7 质量与可观测** | 从"感觉还行"到"能证明没变差" | 回归用例集 · 评测口径 · 成本指标 · 变更流程 |
| **8 交付上线** | 本地三件套 → 可部署可回滚 | 容器化 · 环境分离 · 备份恢复 · 上线 checklist |

**推荐路线（作品集目标）**：`0 → 1 → 2 → 3 → 4 →（5 的最小集）→（7 的用例集）`，把 6、8 简化。
**先走完 0→4 再决定是否升级为完整产品路线。**

### 下一步（Codex 可立即执行的最高价值动作）

1. **【最高优先 / 无依赖】补 `.gitignore` + 从 `config/settings.py` docstring 移除明文密钥** —— 成本 5 分钟，收益极大
2. **修 `plan/validator.py:110` 的 `KeyError`** —— 改为查不到意图时走澄清而非抛异常
3. **扩充 `KnowledgeChunk` 契约**（加 `score` / `source`）—— 这是后续接入任何检索的**前置条件**
4. **反向导出建表脚本** —— 从虚拟机 MySQL 用 `mysqldump --no-data` 导出两库结构，补进仓库

---

## 9. Codex 接入上下文（**本节最重要，请优先阅读**）

### 9.1 首次应优先阅读的文件（推荐顺序）

| 顺序 | 文件 | 为什么先读它 |
| --- | --- | --- |
| 1 | 本文 `CODEX_HANDOFF.md` | 全局上下文 + 约束 |
| 2 | `docs/电商小二二次开发阶段规划.md` | 现状盘点（§1.4/1.5 是缺陷全表）+ 九阶段路线 |
| 3 | `construction_service/api/app.py` | 应用装配入口，`lifespan` 揭示启动时发生什么 |
| 4 | `construction_service/services/dialogue_service.py` | **唯一事务边界**，理解 IO 集中在哪里 |
| 5 | `construction_service/engine/dialogue_engine.py` | 顶层调度，三轨道分流逻辑 |
| 6 | `construction_service/domain/state.py` | 状态聚合根，理解"状态集中"的含义 |
| 7 | `construction_service/plan/validator.py` | 校验口径（含缺陷 2） |
| 8 | `flow_config/user_flows.yml` | 业务 6 流程，理解"YAML 描述流程" |
| 9 | `customer-service-backend/.env.example` | **若存在**，配置项全貌；不存在则读 `config/settings.py` + `.env` |

**必读配置项**

| 配置 | 位置 | 说明 |
| --- | --- | --- |
| `LLM_MODEL` / `LLM_BASE_URL` / `LLM_API_KEY` | `customer-service-backend/.env` | LLM 接入凭据 |
| `COMMERCE_API_BASE_URL` | 同上 | **业务中台地址**（改环境时必须改这里） |
| `DATABASE_URL` | 同上 | 状态库地址（aiomysql 异步方言） |
| `APP_HOST` / `APP_PORT` | 同上 | 默认 `0.0.0.0:18082` |
| `avatar_*` | `config/settings.py` | 数字人 5 项配置（当前未启用） |

### 9.2 常见二次开发任务示例

| 任务 | 改哪里 | 注意事项 |
| --- | --- | --- |
| **新增一条业务流程** | ① `flow_config/user_flows.yml` 加流程定义 ② `task/action/customer/` 加业务动作（如需要） ③ 提示词里的"可选流程清单"同步 | 改完**必须**跑 `check_flows.py` + `check_steps.py`；动作会被自动扫描注册，无需手动登记 |
| **新增一个知识意图** | ① `knowledge/intents.py` 注册意图 ② 对应 Provider 实现检索 ③ `turn_plan.jinja2` 里的意图清单同步 | ⚠️ 新增意图若指向占位 Provider，等于没接 |
| **接入真实 RAG 检索** | ① **先扩** `knowledge/providers/base.py` 的 `KnowledgeChunk`（加 score/source） ② 实现 `RAGProvider.retrieve()` ③ 定 `top_k` / 阈值配置位 | **顺序不能反**（见 §7.1 缺陷 10）；教学文档说这是"轻量改动"不成立 |
| **替换业务对象类型**（如 order → 新对象） | ① `flow_config/*.yml` 槽位名 ② **`task/flow/executor.py:245-251`（硬编码）** ③ **`engine/dialogue_engine.py`（硬编码）** ④ **前端 `App.vue` 卡片模板（硬编码）** ⑤ `knowledge/intents.py` 的 `requires_object` | **三处硬编码必改**，不是配置能解决的（缺陷 3） |
| **改提示词** | `prompts/jinja2/*.jinja2`（4 个模板） | 无回归测试，改完手工跑三条轨道对比 |
| **改 LLM 模型 / 参数** | `customer-service-backend/.env` 的 `LLM_MODEL`；`temperature` / `timeout` 在 `infrastructure/llm_client.py`（硬编码） | `temperature=0` 是有意为之（结构化输出稳定性），**不要随意调高** |
| **新增 HTTP 接口** | `api/router/` 加路由 → `api/app.py` 注册 → `api/schemas.py` 加数据模型 | 保持"路由薄、逻辑在 service"的分层 |
| **改前端界面** | `customer-service-frontend/src/App.vue`（3064 行单文件） | 产品化改造需先拆分（规划阶段 5） |

### 9.3 必须遵守的约束

#### 🚫 禁止修改 / 触碰

| 对象 | 原因 |
| --- | --- |
| `customer-service-backend/.env` | 含真实凭据，**不要提交、不要打印内容、不要改写**（除非用户明确要求） |
| `customer-service-backend/.venv/` | 手工构建的环境，**不要重建、不要 `uv sync`**（会破坏现有环境） |
| `ecommerce-service-backend/.env` | 同上（虽然当前不生效） |
| 虚拟机上的 MySQL 数据 | **不要执行 `DROP` / `DELETE` / `TRUNCATE`**；业务中台的写接口只用于测试，会产生真实记录 |
| `flow_config/*.yml` 的**已有流程 ID** | 已被 `system_flows.yml` 与代码交叉引用，改名会断链 |

#### ⚠️ 必须人工复核的改动（改完要用户确认）

| 类型 | 为什么 |
| --- | --- |
| `plan/validator.py` 的校验口径 | 直接决定"幻觉是否被拦住"，属契约层面 |
| `domain/state.py` 的序列化 / 反序列化 | 改错会导致存量状态数据不兼容 |
| `repository/dialogue_repository.py` 的 upsert | 直接操作持久化，改错会写坏状态 |
| `KnowledgeChunk` 契约变更 | 影响所有 Provider，需一次性对齐 |
| `prompts/jinja2/*.jinja2` | 无测试保护，行为变化难以自动验证 |
| 任何涉及 `sender_id` 的改动 | 涉及身份体系，牵一发动全身 |

#### 🔐 敏感信息处理

| 规则 | 说明 |
| --- | --- |
| **绝不在文档 / 提交信息 / 日志中输出真实密钥** | 包括 `LLM_API_KEY`、`avatar_access_key_secret`、MySQL 密码 |
| **不把 `.env` 内容写进任何交付文件** | 引用配置项时只写**键名**，不写值 |
| **`config/settings.py` 的 docstring 必须清理** | 那里有明文 key（缺陷 1）——这是 Codex 首轮**应该主动处理**的 |
| **新增敏感配置只走 `.env`** | 不要写进代码、不要写进 YAML 的明文段 |
| **建库建表脚本若含密码，用占位符** | 例如 `mysql://user:${DB_PASSWORD}@host/db` |

#### ✅ 改动前必做的动作

```
1. 确认目标文件属于【通用层】还是【业务层】（见 §3.3 表的最后一列）
2. 通用层改动 → 影响面大，先向用户说明
3. 业务层改动 → 相对安全，但仍需验证三条轨道
4. 任何改动前，先手工备份目标文件（本仓库无 git，无版本回滚）
5. 改动后跑：check_flows.py + check_steps.py（若涉及流程）+ 三条轨道手工验证
```

### 9.4 建议的接续起手式

**新会话第一轮，建议先做这三件事，再动手改代码：**

1. 读 §0 + §9.1 列出的前 5 个文件 —— 建立全局认知
2. 按 §4.2 顺序启动三件套，确认 `curl http://127.0.0.1:18082/hello` 返回 `{"success":"ok"}` —— 确认基线可用
3. 读 §7.1 缺陷表，确认当前任务是否与某个已知缺陷冲突

**如果新任务是「改造业务」** → 先读 `docs/电商小二二次开发阶段规划.md` 第二部分（九阶段），按阶段推进，不要跳阶段。

**如果新任务是「接入 RAG / 知识库」** → 必须先读 §7.1 缺陷 9、10，理解"先扩契约、再写检索"的顺序。

**如果新任务是「修复 bug」** → 先查 §7.1 缺陷表，可能已有记录与定位。

---

## 附 · 待补充内容清单（用户需确认）

| # | 待补充项 | 位置 |
| --- | --- | --- |
| 1 | 项目起止时间、本人角色 | §1 |
| 2 | 部署环境细节（虚拟机配置、Docker 版本等） | §2.4 |
| 3 | 是否有未纳入仓库的建表脚本 | §7.2 |
| 4 | 数字人功能是否需要启用 | §5.5 |
| 5 | 是否已有既定的编码规范文档 | §6.1 |
| 6 | 目标业务方向（要改造成什么产品） | §8 / §1 |
| 7 | 是否有性能基线数据（QPS / 延迟） | §5.3 |

## 附 · 文档地图

| 想了解 | 读 |
| --- | --- |
| **改造全流程与阶段编排** | `docs/电商小二二次开发阶段规划.md` ← 权威规划文档 |
| **业务中台接口** | `ecommerce-service-backend/README.md` |
| 教学资料（原项目设计文档） | `D:\桌面\资料文档\sgg\电商小二资料\`（⚠️ 有编号冲突与失效图片，见规划 §1.6） |
| 原教学项目源码 | `github.com/2019hzk/260119-ecommerce-customer` |
