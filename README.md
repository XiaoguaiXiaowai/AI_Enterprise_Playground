# AI Enterprise Playground

Production-style AI engineering playground.

## Quickstart

### Docker Compose

1. Copy env file:

   - `cp .env.example .env`

2. Start:

   - `docker compose up --build`

3. Open:

   - API: `http://localhost:8000/`
   - Swagger: `http://localhost:8000/docs`
   - Health: `http://localhost:8000/health`
   - Versioned API: `http://localhost:8000/api/v1/health`
   - WebSocket: `ws://localhost:8000/ws` (or `ws://localhost:8000/api/v1/ws`)

### Local (backend)

- `python3.12 -m venv .venv && source .venv/bin/activate`
- `pip install -r backend/requirements.txt`
- `alembic -c backend/alembic.ini upgrade head`
- `uvicorn app.main:app --reload --app-dir backend`

### GitHub OAuth

- Callback URL: `http://localhost:8000/auth/github/callback`
- Required env:
  - `GITHUB_CLIENT_ID`
  - `GITHUB_CLIENT_SECRET`

### Local (frontend)

- `cd frontend`
- `cp .env.example .env.local` (optional)
- `npm install`
- `npm run dev`

## Chat

### REST

- Create session: `POST /chat/sessions`
- List sessions: `GET /chat/sessions`
- List messages: `GET /chat/sessions/{session_id}/messages`
- Send message (non-stream): `POST /chat/sessions/{session_id}/messages`

### WebSocket

- Connect: `ws://localhost:8000/ws?token=<access_token>`
- Send:
  - `{"type":"chat.run","session_id":1,"content":"hi","model":"mock"}`
- Receive events:
  - `connected` → `thinking` → multiple `token` → `completed`

## Guardrails

- Evaluate: `POST /guardrails/evaluate`
- Chat is guarded:
  - Input block returns 400 with `detail.error=guard_failed` and `detail.stage=input`
  - Output block returns 400 with `detail.stage=output` and stores assistant as `[blocked_by_guardrails]`

## Memory

- Create: `POST /memory`
- List: `GET /memory?namespace=default&memory_type=short`
- Timeline: `GET /memory/timeline`
- Recall: `POST /memory/recall`

## Context

- Current request context: `GET /context/current`
- Recent context events: `GET /context/events` (requires auth)

## RAG

- Upload: `POST /rag/upload` (multipart form field: `file`)
- Documents: `GET /rag/documents`
- Delete document: `DELETE /rag/documents/{document_id}`
- Search: `POST /rag/search`
- Answer: `POST /rag/answer`
- View source chunk: `GET /rag/chunks/{chunk_id}`

## MCP

- Register server: `POST /mcp/servers`
- List servers: `GET /mcp/servers`
- List tools: `GET /mcp/servers/{server_id}/tools`
- Call tool: `POST /mcp/servers/{server_id}/tools/{tool_name}`
- Audit calls: `GET /mcp/calls`

Demo servers (stdio):

- Filesystem:
  - `config.command`: `[python, -m, app.mcp_servers.filesystem_server]`
  - `config.env.MCP_FILESYSTEM_ROOT`: restricts access to a root directory
- SQL (read-only):
  - `config.command`: `[python, -m, app.mcp_servers.sql_server]`
  - `config.env.MCP_DATABASE_URL`: database connection string (defaults to app DB)

## Agents

- Run: `POST /agents/runs`
- Resume run: `POST /agents/runs/{run_id}/resume`
- List runs: `GET /agents/runs`
- Get run: `GET /agents/runs/{run_id}`

## HITL

- List requests: `GET /hitl/requests`
- Get request: `GET /hitl/requests/{hitl_request_id}`
- Approve: `POST /hitl/requests/{hitl_request_id}/approve`
- Reject: `POST /hitl/requests/{hitl_request_id}/reject`
- Edit: `POST /hitl/requests/{hitl_request_id}/edit`
- Resume: `POST /hitl/requests/{hitl_request_id}/resume`

## Dashboard

- Overview: `GET /dashboard/overview?hours=24&hitl_pending_limit=20&hitl_pending_offset=0`
