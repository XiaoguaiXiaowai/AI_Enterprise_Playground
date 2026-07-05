# AI Enterprise Playground

## Development Plan v1.0 (Vibe Coding Edition)

> Goal: Build a production-style AI engineering portfolio project that
> demonstrates FastAPI, LangChain/LangGraph, MCP, RAG, multi-agent
> systems, authentication, and engineering practices.

------------------------------------------------------------------------

# 1. Vision

## Core positioning

An extensible enterprise AI platform rather than a chatbot.

Core principles:

-   Modular architecture
-   API-first
-   Plugin-based AI modules
-   Production engineering practices
-   Easy to extend with future AI technologies

## Success Criteria

-   Deployable by Docker Compose
-   Swagger available
-   GitHub ready
-   Personal website integration
-   Every module independently demo-able

------------------------------------------------------------------------

# 2. Recommended Tech Stack

## Backend

-   Python 3.12+
-   FastAPI
-   Pydantic v2
-   SQLAlchemy
-   Alembic
-   Uvicorn
-   httpx
-   structlog
-   slowapi (rate limit)

## AI

-   LangChain
-   LangGraph
-   MCP SDK
-   OpenAI SDK
-   Chroma (later PGVector)

## Database

MVP: - SQLite - Chroma

Production: - PostgreSQL - Redis - PGVector

## Frontend

-   Next.js
-   React
-   TailwindCSS
-   shadcn/ui

## DevOps

-   Docker
-   Docker Compose
-   GitHub Actions
-   Nginx

------------------------------------------------------------------------

# 3. Suggested Repository Structure

``` text
ai-enterprise-playground/

backend/
frontend/
docs/
docker/
scripts/
examples/
tests/

README.md
```

Backend:

``` text
app/
 api/
 core/
 config/
 middleware/
 security/
 services/
 modules/
 models/
 schemas/
 repositories/
 storage/
 utils/
 tests/
```

Every module:

``` text
module_name/

router.py
service.py
graph.py
prompt.py
schemas.py
repository.py
config.py
demo.py
README.md
tests/
```

------------------------------------------------------------------------

# 4. Cross-cutting Features

Every module should support when applicable:

-   Authentication
-   Authorization
-   Logging
-   Request ID
-   Metrics
-   Error handling
-   Streaming
-   OpenAPI
-   Unit tests
-   Integration tests

------------------------------------------------------------------------

# 5. Sprint Plan

## Sprint0 Infrastructure

Deliverables

-   Project initialization
-   Docker
-   Health endpoint
-   Swagger
-   Config management
-   Environment variables

Endpoints

-   GET /
-   GET /health
-   GET /version

Acceptance

-   docker compose up works
-   docs accessible

------------------------------------------------------------------------

## Sprint1 Authentication

Functions

-   Register
-   Login
-   Refresh Token
-   JWT
-   BCrypt hashing
-   Google OAuth
-   GitHub OAuth
-   Microsoft OAuth
-   Email verification
-   RBAC

Tables

-   users
-   roles
-   permissions

Endpoints

-   POST /auth/login
-   POST /auth/register
-   POST /auth/refresh
-   GET /auth/me

------------------------------------------------------------------------

## Sprint2 FastAPI Engineering

Features

-   Middleware
-   Request logging
-   Correlation ID
-   Global Exception Handler
-   Rate Limiter
-   Background Tasks
-   Dependency Injection
-   API Versioning

------------------------------------------------------------------------

## Sprint3 Realtime

Features

-   WebSocket
-   Token Streaming
-   Progress notification

Events

-   connected
-   thinking
-   searching
-   completed
-   failed

------------------------------------------------------------------------

## Sprint4 Chat

Capabilities

-   Conversation
-   Streaming
-   History
-   Multi-model switching

Provider abstraction

-   OpenAI
-   Claude
-   Gemini
-   Ollama

------------------------------------------------------------------------

## Sprint5 Guardrails

Showcase

-   Prompt Injection detection
-   PII detection
-   Toxicity
-   Custom Guard
-   Guard Chains

Pipeline

Input -\> Guard -\> LLM -\> Output Guard

------------------------------------------------------------------------

## Sprint6 Memory

Features

-   Short-term memory
-   Long-term memory
-   Namespace
-   Recall
-   Update

Visualization

Timeline + Memory Inspector

------------------------------------------------------------------------

## Sprint7 Context Engineering

Display

-   Runtime Context
-   State
-   Storage
-   Lifecycle Context

Developer panel

-   Current Context
-   Tokens
-   Active tools

------------------------------------------------------------------------

## Sprint8 Hybrid RAG

Pipeline

Upload PDF

Chunk

Embedding

Hybrid Retrieval

Re-ranking

LLM

Citation

Features

-   Upload
-   Delete
-   Search
-   Source Viewer

------------------------------------------------------------------------

## Sprint9 MCP

Support

-   stdio
-   SSE
-   Streamable HTTP

Servers

-   Filesystem
-   SQL
-   GitHub
-   Browser

------------------------------------------------------------------------

## Sprint10 Multi-Agent

Agents

-   Planner
-   Researcher
-   Coder
-   Reviewer

Visual workflow graph

------------------------------------------------------------------------

## Sprint11 Human In The Loop

States

Pending Approval

Approved

Rejected

Edited

Resume execution

------------------------------------------------------------------------

## Sprint12 Dashboard

Widgets

-   Module cards
-   Recent runs
-   Token usage
-   Cost
-   Logs
-   Health
-   Active sessions

------------------------------------------------------------------------

# 6. Database (MVP)

users roles permissions chat_sessions messages documents chunks memories
agent_runs audit_logs

------------------------------------------------------------------------

# 7. REST API Groups

/auth /chat /rag /memory /context /guardrails /mcp /agents /hitl /admin

------------------------------------------------------------------------

# 8. Personal Website Pages

-   Home
-   Architecture
-   Playground
-   API Docs
-   Modules
-   Blog
-   Changelog

Every module page contains

-   Introduction
-   Live Demo
-   API
-   Architecture
-   Screenshots
-   Source Code
-   Lessons Learned

------------------------------------------------------------------------

# 9. Future Roadmap

v1.1 LangGraph Workflow

v1.2 OpenTelemetry

v1.3 Redis Queue

v1.4 PostgreSQL + PGVector

v1.5 Kubernetes

v2.0 Multi-tenant

v2.1 CrewAI / LlamaIndex / A2A

------------------------------------------------------------------------

# 10. Definition of Done

Each sprint is complete only if:

-   Code merged
-   README updated
-   APIs documented
-   Docker works
-   Tests pass
-   Demo page available
-   GitHub screenshot updated
