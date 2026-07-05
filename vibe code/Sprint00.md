🌟🌟🌟🌟🌟
`/Users/lijia/Documents/02.Coder/AI_Enterprise_Playground/AI_Enterprise_Playground_Development_Plan_v1.0.md` 根据开发文档分阶段的实现这套系统

🌟🌟🌟🌟🌟

toolName: todo\_write

status: success

Todos updated: 13 items

下面给你一套“按开发文档分阶段落地”的实现路线，把 [AI\_Enterprise\_Playground\_Development\_Plan\_v1.0.md](file:///Users/lijia/Documents/02.Coder/AI_Enterprise_Playground/AI_Enterprise_Playground_Development_Plan_v1.0.md) 里的 Sprint0～Sprint12 变成可执行的交付物清单与实现顺序。你可以按“每个 Sprint 都能独立演示、可 Docker Compose 一键跑、Swagger 可用、测试可跑”的方式推进。

***

**总体实施原则（贯穿全部 Sprint）**

- 代码组织：严格按文档的 `backend/app/{api,core,config,middleware,security,services,modules,...}` 分层；新增能力优先做成 `modules/<module_name>/...` 插件化结构。
- 交付节奏：每个 Sprint 形成一个“可运行的最小闭环”，包含：API + OpenAPI + demo 路径/页面（哪怕是最简）+ 测试（至少冒烟）+ README 更新。
- 先打地基再堆能力：Sprint0→1→2 是所有后续的前置；Realtime/Streaming（Sprint3）最好在 Chat（Sprint4）之前完成，否则后面要返工接口形态。

***

## Sprint0：基础设施（工程可启动 + 可观测最小集）

**目标**：仓库骨架 + docker compose up 可跑 + 3 个基础端点 + Swagger

**实现清单**

- 仓库结构初始化（backend/frontend/docs/docker/scripts/examples/tests/）
- FastAPI 应用工厂、配置管理（env + 分环境）
- `/`、`/health`、`/version` 三端点
- OpenAPI/Swagger 可访问
- Dockerfile + docker-compose（至少 backend + 数据库/存储的占位配置）
- 最小日志（先简单，Sprint2 再“工程化”）

**验收**

- `docker compose up` 后：health 200，Swagger 可打开，/version 返回版本信息

***

## Sprint1：认证与授权（能真实保护后续模块）

**目标**：注册/登录/刷新 + JWT + 密码哈希 + RBAC 框架落库

**实现清单**

- 数据表：`users / roles / permissions`（先满足 MVP，后续可扩展多租户）
- 接口：`POST /auth/register`、`POST /auth/login`、`POST /auth/refresh`、`GET /auth/me`
- 安全：
  - BCrypt 哈希
  - Access Token + Refresh Token（刷新逻辑、token 失效策略）
  - RBAC：依赖注入式权限校验（例如 `require_permission("xxx")`）
- 测试：登录/刷新/权限拦截冒烟

**建议取舍**

- OAuth（Google/GitHub/Microsoft）可以先“预留接口与表结构”，作为 Sprint1.5 或 Sprint2 后插入，避免拖慢主线。

***

## Sprint2：FastAPI 工程化（把“可用”变成“可维护”）

**目标**：中间件、全局异常、请求链路标识、限流、DI、版本化

**实现清单**

- Middleware：
  - RequestID/CorrelationID（写入响应头，注入日志上下文）
  - 请求日志（入参/耗时/状态码；注意脱敏）
- 全局异常处理：统一错误响应结构（含 request\_id）
- Rate Limiter：slowapi（对登录/聊天等关键接口）
- Background Tasks：为后续 RAG 入库、异步 embedding 做铺垫
- API Versioning：例如 `/api/v1/...` 或基于 header
- 规范化 settings、router 注册、依赖注入组织方式

**验收**

- 发生异常时返回统一错误结构；每个请求都有 request\_id；限流对关键接口生效

***

## Sprint3：Realtime + Streaming（后续 Chat/RAG 的接口形态定型）

**目标**：建立“事件流协议”，支持 thinking/searching/completed/failed 等事件

**实现清单**

- WebSocket 或 SSE 二选一（也可两者都支持，但建议先选一种定主线）
- 事件定义：`connected / thinking / searching / completed / failed`（文档已给）
- Token Streaming：后端统一用“事件流输出”适配不同 LLM provider
- 前端先做最小订阅 demo（哪怕是简单页面打印事件）

***

## Sprint4：Chat（会话闭环 + Provider 抽象）

**目标**：支持对话、历史、流式输出、多模型切换

**实现清单**

- 表：`chat_sessions / messages`
- API：
  - 创建会话、发送消息、拉取历史
  - 流式发送（复用 Sprint3 事件协议）
- Provider 抽象层：
  - 先实现 OpenAI（或你当前最确定的一个）
  - Claude/Gemini/Ollama 作为后续 provider 插件逐步补齐
- 最小 UI：会话列表 + 对话窗口 + 流式渲染

***

## Sprint5：Guardrails（把安全链路做成可插拔管线）

**目标**：Input Guard → LLM → Output Guard 的可组合管线

**实现清单**

- Guard 类型：提示注入、PII、toxicity（先实现规则/轻量模型，后续再升级）
- 每个 guard 输出结构化结果（pass/fail + reason + score）
- 在 Chat 请求链路中可配置启用（例如按用户/角色/环境）

***

## Sprint6：Memory（短期/长期 + 命名空间）

**目标**：可存、可召回、可更新，且能按 namespace 管理

**实现清单**

- 表：`memories`（短期可直接 DB；长期可向量库/混合存储）
- API：Recall/Update/Namespace 管理
- 可视化：Timeline + Memory Inspector（先做后端接口，前端做最小展示）

***

## Sprint7：Context Engineering（开发者面板）

**目标**：把运行态上下文（state、storage、lifecycle）“看得见”

**实现清单**

- 采集：每次 agent/chat/run 的上下文快照（注意不要存敏感信息）
- 面板：当前上下文、token 使用、活跃工具/链路信息

***

## Sprint8：Hybrid RAG（上传→检索→引用的完整闭环）

**目标**：PDF 上传、切分、embedding、混合检索、重排、引用展示

**实现清单**

- 表：`documents / chunks`
- 管线：
  - 上传（文件存储 + 元数据）
  - chunk（可配置 chunk\_size/overlap）
  - embedding（先 Chroma，后续 PGVector）
  - Hybrid Retrieval（关键词 + 向量）
  - Re-ranking（先简单规则/模型，后续升级）
  - Citation（chunk id + 页码/位置 + 原文片段）
- 前端：Source Viewer（点击引用可定位）

***

## Sprint9：MCP（把“工具能力”标准化接入）

**目标**：支持 stdio/SSE/HTTP 的 MCP 客户端能力，接入 Filesystem/SQL/GitHub/Browser

**实现清单**

- MCP 连接管理（server registry + 权限控制）
- Tool 调用审计（后续接 Sprint11 HITL）
- 最小演示：让 agent 能调用 filesystem/sql，返回结构化结果

***

## Sprint10：Multi-Agent（把系统从“应用”变成“平台”）

**目标**：Planner/Researcher/Coder/Reviewer 多 agent 协作 + 可视化工作流图

**实现清单**

- agent 定义与编排（建议用 LangGraph）
- 运行记录：`agent_runs`（文档也列了）
- 可视化：展示节点、边、状态、耗时、失败原因

***

## Sprint11：HITL（可控、可审计、可恢复）

**目标**：审批状态机 + 暂停/恢复执行

**实现清单**

- 状态：Pending/Approved/Rejected/Edited/Resume
- 审批点：高风险 tool（filesystem 写、外部 API、付款等）
- 审计：`audit_logs`（谁在何时批准了什么）

***

## Sprint12：Dashboard（面向展示与运营的“首页”）

**目标**：模块卡片、最近 runs、token/cost、日志、健康、活跃会话

**实现清单**

- 聚合 API（按模块/时间范围）
- 前端首页：可作为你个人网站的“Playground”入口

***

**我需要你确认的 3 个选择（会影响落地细节）**

- 认证范围：你希望 Sprint1 先只做“账号密码 + JWT”，OAuth 全部后置；还是要同时做 1 个 OAuth（例如 GitHub）？
- Realtime 方案：Sprint3 你更想用 SSE 还是 WebSocket 作为主通道？
- 数据库策略：MVP 阶段是否确认 SQLite + Chroma（文档推荐），还是你希望直接上 PostgreSQL（减少后续迁移）？

你回复这三点后，我可以把 Sprint0～Sprint2 细化到“具体目录/文件清单 + 路由/Schema/表结构 + 每个接口请求响应样例”，并按你选择的路线开始逐 Sprint 实现。

🌟🌟🌟🌟🌟

- 认证范围：你希望 Sprint1 先只做“账号密码 + JWT”，OAuth 全部后置；还是要同时做 1 个 OAuth（例如 GitHub）？
  回答：同时做 1 个 OAuth（例如 GitHub）
- Realtime 方案：Sprint3 你更想用 SSE 还是 WebSocket 作为主通道？
  回答：WebSocket
- 数据库策略：MVP 阶段是否确认 SQLite + Chroma（文档推荐），还是你希望直接上 PostgreSQL（减少后续迁移）？
  回答：SQLite + Chroma（文档推荐）
  🌟🌟🌟🌟🌟
  toolName: no\_need\_execute

status: no\_need\_execute

toolName: search\_by\_regex

status: failed

query: Sprint0|sprint 0|sprint0|里程碑|后端|前端|docker

toolName: view\_folder

status: failed

/Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground

toolName: view\_files

status: failed

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/AI\_Enterprise\_Playground\_Development\_Plan\_v1.0.md

已对当前项目根目录做了完整扫描：目前仓库里只有一份开发计划文档，没有任何 backend/frontend/docker 代码或配置落地。

**当前目录结构（实际存在）**

- 根目录：`/Users/lijia/Documents/02.Coder/AI_Enterprise_Playground/`
- 唯一文件：[AI\_Enterprise\_Playground\_Development\_Plan\_v1.0.md](file:///Users/lijia/Documents/02.Coder/AI_Enterprise_Playground/AI_Enterprise_Playground_Development_Plan_v1.0.md)

**Sprint0（Infrastructure）完成情况判断**

- 已完成：
  - 仅有 Sprint0 的规划说明（在开发计划文档中定义了 deliverables/endpoints/acceptance）
- 未完成（均未看到对应代码/配置落地）：
  - Project initialization（仓库结构未创建：backend/ frontend/ docker/ 等目录不存在）
  - Docker / Docker Compose（未找到 `Dockerfile`、`docker-compose.yml` 等）
  - Health endpoint（未找到 FastAPI 入口与路由实现）
  - Swagger（未找到 FastAPI 应用与 OpenAPI 文档入口）
  - Config management / Environment variables（未找到配置模块、`.env`、settings 等）

**关键文件路径（用于核对 Sprint0 计划与验收项）**

- Sprint 计划与验收标准来源文档：\[AI\_Enterprise\_Playground\_Development\_Plan\_v1.0.md]\(file:///Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/AI\_Enterprise\_Playground\_Development\_Plan\_v1.0.md#L

toolName: AskUserQuestion

status: success

toolName: view\_folder

status: success

/Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground

toolName: apply\_patch

status: failed

toolName: write\_to\_file

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/README.md

content: undefined

toolName: apply\_patch

status: failed

toolName: write\_to\_file

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/.env.example

content: undefined

toolName: apply\_patch

status: failed

toolName: write\_to\_file

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/docker-compose.yml

content: undefined

toolName: apply\_patch

status: failed

toolName: edit\_file\_update

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/docker-compose.yml

changes:

toolName: apply\_patch

status: failed

toolName: write\_to\_file

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/backend/Dockerfile

content: undefined

toolName: apply\_patch

status: failed

toolName: write\_to\_file

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/backend/requirements.txt

content: undefined

toolName: apply\_patch

status: failed

toolName: write\_to\_file

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/backend/app/__init__.py

content: undefined

toolName: apply\_patch

status: failed

toolName: write\_to\_file

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/backend/app/config/__init__.py

content: undefined

toolName: apply\_patch

status: failed

toolName: write\_to\_file

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/backend/app/config/settings.py

content: undefined

toolName: apply\_patch

status: failed

toolName: write\_to\_file

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/backend/app/api/__init__.py

content: undefined

toolName: apply\_patch

status: failed

toolName: write\_to\_file

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/backend/app/api/router.py

content: undefined

toolName: apply\_patch

status: failed

toolName: write\_to\_file

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/backend/app/main.py

content: undefined

toolName: apply\_patch

status: failed

toolName: write\_to\_file

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/backend/tests/test\_system\_endpoints.py

content: undefined

toolName: apply\_patch

status: failed

toolName: write\_to\_file

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/.gitignore

content: undefined

toolName: run\_command

status: success

command: npx create-next-app\@latest frontend --ts --tailwind --eslint --app --src-dir --import-alias "@/\*" --use-npm undefined

toolName: view\_folder

status: success

/Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground

toolName: check\_command\_status

status: success

toolName: view\_folder

status: failed

/Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/frontend

toolName: run\_command

status: success

command: node -v && npm -v undefined

toolName: run\_command

status: success

command: python -V undefined

toolName: run\_command

status: success

command: python3 -V undefined

toolName: run\_command

status: success

command: which node || true; which npm || true; node -v || true; npm -v || true undefined

toolName: run\_command

status: success

command: npx --yes create-next-app\@latest frontend --ts --tailwind --eslint --app --src-dir --import-alias "@/\*" --use-npm undefined

toolName: run\_command

status: success

command: mkdir -p .xdg && XDG\_CONFIG\_HOME="$(pwd)/.xdg" npx --yes create-next-app\@latest frontend --ts --tailwind --eslint --app --src-dir --import-alias "@/\*" --use-npm undefined

toolName: apply\_patch

status: failed

toolName: write\_to\_file

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/frontend/package.json

content: undefined

toolName: apply\_patch

status: failed

toolName: write\_to\_file

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/frontend/next-env.d.ts

content: undefined

toolName: apply\_patch

status: failed

toolName: write\_to\_file

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/frontend/tsconfig.json

content: undefined

toolName: apply\_patch

status: failed

toolName: write\_to\_file

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/frontend/next.config.mjs

content: undefined

toolName: apply\_patch

status: failed

toolName: edit\_file\_update

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/frontend/next.config.mjs

changes:

toolName: apply\_patch

status: failed

toolName: write\_to\_file

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/frontend/postcss.config.mjs

content: undefined

toolName: apply\_patch

status: failed

toolName: write\_to\_file

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/frontend/tailwind.config.ts

content: undefined

toolName: apply\_patch

status: failed

toolName: write\_to\_file

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/frontend/src/app/layout.tsx

content: undefined

toolName: apply\_patch

status: failed

toolName: write\_to\_file

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/frontend/src/app/page.tsx

content: undefined

toolName: apply\_patch

status: failed

toolName: write\_to\_file

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/frontend/src/app/globals.css

content: undefined

toolName: apply\_patch

status: failed

toolName: edit\_file\_update

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/frontend/src/app/layout.tsx

changes:

toolName: apply\_patch

status: failed

toolName: write\_to\_file

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/frontend/.eslintrc.json

content: undefined

toolName: apply\_patch

status: failed

toolName: write\_to\_file

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/frontend/.gitignore

content: undefined

toolName: run\_command

status: success

command: python3 -m pip install -r backend/requirements.txt && python3 -m pytest -q undefined

toolName: apply\_patch

status: failed

toolName: edit\_file\_update

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/backend/requirements.txt

changes:

toolName: run\_command

status: success

command: python3 -m pip install -r backend/requirements.txt && python3 -m pytest -q undefined

toolName: run\_command

status: success

command: python3.12 -V || true; python3.13 -V || true; python3.11 -V || true undefined

toolName: run\_command

status: success

command: python3.12 -m pip install -r backend/requirements.txt && python3.12 -m pytest -q undefined

toolName: run\_command

status: success

command: python3.12 -m venv .venv && source .venv/bin/activate && pip install -r backend/requirements.txt && pytest -q undefined

toolName: apply\_patch

status: failed

toolName: write\_to\_file

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/backend/tests/conftest.py

content: undefined

toolName: run\_command

status: success

command: source .venv/bin/activate && pytest -q undefined

toolName: run\_command

status: success

command: npm install undefined

toolName: run\_command

status: success

command: npm run build undefined

toolName: apply\_patch

status: failed

toolName: edit\_file\_update

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/README.md

changes:

toolName: apply\_patch

status: failed

toolName: edit\_file\_update

status: success

filePath: /Users/lijia/Documents/02.Coder/AI\_Enterprise\_Playground/docker-compose.yml

changes:

toolName: todo\_write

status: success

Todos updated: 13 items

toolName: GetDiagnostics

status: success

已按你的选择（账号密码 + JWT + GitHub OAuth、Realtime 走 WebSocket、MVP 用 SQLite + Chroma）把 Sprint0 的工程骨架先落地起来了：现在仓库已经具备可启动的 FastAPI + 基础端点 + Swagger、Dockerfile/docker-compose、以及可构建的 Next.js + Tailwind 前端骨架。

**Sprint0 已完成内容**

- 后端 FastAPI 骨架与 3 个端点：
  - `/`、`/health`、`/version`（见 [router.py](file:///Users/lijia/Documents/02.Coder/AI_Enterprise_Playground/backend/app/api/router.py)、[main.py](file:///Users/lijia/Documents/02.Coder/AI_Enterprise_Playground/backend/app/main.py)）
- 配置管理（Pydantic Settings，支持 env 覆盖）：[settings.py](file:///Users/lijia/Documents/02.Coder/AI_Enterprise_Playground/backend/app/config/settings.py)
- Docker 化：
  - 后端镜像： [backend/Dockerfile](file:///Users/lijia/Documents/02.Coder/AI_Enterprise_Playground/backend/Dockerfile)
  - `docker-compose.yml`：backend + postgres（backend 默认仍用 SQLite，postgres 用于后续迁移/切换）：[docker-compose.yml](file:///Users/lijia/Documents/02.Coder/AI_Enterprise_Playground/docker-compose.yml)
- 测试冒烟：`pytest` 覆盖 3 个系统端点：[test\_system\_endpoints.py](file:///Users/lijia/Documents/02.Coder/AI_Enterprise_Playground/backend/tests/test_system_endpoints.py)
- 前端骨架（Next.js 14 + Tailwind，可 build）：[frontend](file:///Users/lijia/Documents/02.Coder/AI_Enterprise_Playground/frontend/package.json)

**怎么跑起来**

- 后端（本地）
  - `python3.12 -m venv .venv && source .venv/bin/activate`
  - `pip install -r backend/requirements.txt`
  - `uvicorn app.main:app --reload --app-dir backend`
  - Swagger：`http://localhost:8000/docs`
- 前端（本地）
  - `cd frontend && npm install && npm run dev`
- Docker Compose
  - `docker compose up --build`
  - backend 默认 `DATABASE_URL=sqlite:////data/app.db`（无需 Postgres 也能跑）
  - 如要切到 Postgres：设置 `DATABASE_URL=postgresql+psycopg://ai_playground:ai_playground@postgres:5432/ai_playground`

**进入 Sprint1 前需要你提供 2 个信息（GitHub OAuth 必备）**

- 你的 GitHub OAuth App 计划使用的回调 URL（本地一般类似 `http://localhost:8000/auth/github/callback`）
- 是否接受我用 `Authlib` 来实现 GitHub OAuth（FastAPI 常用方案）；如果你更偏好别的库也可以指定

你确认这两点后，我就开始 Sprint1：建表（users/roles/permissions）+ 注册/登录/refresh + JWT + RBAC + GitHub OAuth 全链路，并把 `/auth/*` 路由与 Alembic 迁移一起补齐。
