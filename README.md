# Event Analytics Platform

A lightweight, open-source alternative to Mixpanel. Multi-tenant event analytics with natural language querying and chart rendering.

## Architecture

```
[SDK/curl] --API Key--> [FastAPI: /events] --> [DuckDB]
[Browser]  --Session-->  [FastAPI: /query]  --> [OpenAI GPT-4o] --> [SQL Sandbox] --> [DuckDB] --> [GPT-4o-mini: Chart Config] --> [React + Recharts]
```

**Tech Stack:**
- **Backend:** Python, FastAPI, DuckDB (embedded analytical database)
- **Frontend:** React, TypeScript, Vite, Tailwind CSS, Recharts
- **LLM:** OpenAI GPT-4o (SQL generation), GPT-4o-mini (chart configuration)
- **SQL Safety:** sqlglot AST-level validation of LLM-generated queries

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- An OpenAI API key

### Setup

```bash
# 1. Clone and install
git clone <repo-url> && cd event-analytics

# Backend dependencies
cd backend && pip3 install -r requirements.txt && cd ..

# Frontend dependencies
cd frontend && npm install && cd ..

# 2. Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 3. Seed demo data (creates org + 15K events)
python3 scripts/seed.py
# Save the API key that is printed!

# 4. Start both servers
./scripts/run_dev.sh
```

Open http://localhost:5173, login with the API key from step 3.

### Try These Queries
- "Show daily active users for the last 30 days"
- "What are the top 5 events this week?"
- "Show conversion from signup to purchase by day"
- "What pages get the most views?"
- "Show hourly event volume for today"

## Architecture Decisions

### Why DuckDB?
DuckDB is an embedded columnar analytical database - think "SQLite for analytics." It was chosen because:
- **No Docker/infrastructure required** - it's a pip install, satisfying the local-only requirement
- **Columnar storage** - optimized for the aggregation queries this platform runs (COUNT, GROUP BY, date_trunc)
- **Standard SQL** - LLM-generated queries work naturally
- **MVCC concurrency** - reads never block writes within the same process

### NL-to-SQL Pipeline (Two-Stage LLM)
The query pipeline makes two LLM calls per question:
1. **GPT-4o** generates the SQL query (accuracy-critical)
2. **GPT-4o-mini** determines chart type and configuration (simpler task, cheaper model)

This separation improves reliability vs. a single prompt that must produce both SQL and visualization config.

### SQL Sandboxing (Defense in Depth)
LLM-generated SQL is untrusted input. The sandbox applies four layers:
1. **Regex blocklist** - catches INSERT, DROP, COPY, file-reading functions, etc.
2. **AST parsing via sqlglot** - structurally validates it's a single SELECT statement
3. **Org ID filter check** - ensures multi-tenant isolation is preserved
4. **LIMIT enforcement** - adds LIMIT 10000 if missing to prevent runaway queries

### Authentication
Two auth mechanisms for two consumers:
- **API Key** (header `X-API-Key`) - for event ingestion from SDKs/scripts. Keys are stored as SHA-256 hashes.
- **Session Cookie** - for the dashboard UI. Login with an API key to get a session.

No passwords - the API key is the shared secret for a local-only tool.

### Multi-Tenant Isolation
- Every event is tagged with `org_id` at ingestion
- The NL-to-SQL prompt hardcodes `WHERE org_id = '{org_id}'` in every query
- The SQL sandbox verifies the org_id filter exists before execution
- Session auth resolves the org from the session token, not from user input

## API Reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/orgs` | None | Create organization (returns API key) |
| `POST` | `/api/v1/auth/login` | None | Login with API key (sets session cookie) |
| `GET` | `/api/v1/auth/me` | Session | Get current org info |
| `POST` | `/api/v1/auth/logout` | None | Clear session cookie |
| `POST` | `/api/v1/events` | API Key | Ingest single event |
| `POST` | `/api/v1/events/batch` | API Key | Ingest batch (up to 1000) |
| `POST` | `/api/v1/query` | Session | Natural language query |
| `GET` | `/api/v1/visualizations` | Session | List saved visualizations |
| `POST` | `/api/v1/visualizations` | Session | Save a visualization |
| `GET` | `/api/v1/visualizations/:id` | Session | Get saved visualization |
| `DELETE` | `/api/v1/visualizations/:id` | Session | Delete visualization |

### Event Ingestion Example

```bash
curl -X POST http://localhost:8000/api/v1/events \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{
    "event": "page_view",
    "distinct_id": "user-123",
    "properties": {"page": "/home", "referrer": "google"}
  }'
```

## Project Structure

```
event-analytics/
├── backend/
│   └── app/
│       ├── main.py              # FastAPI app, lifespan, CORS
│       ├── config.py            # Settings (env vars)
│       ├── dependencies.py      # Auth dependencies
│       ├── db/
│       │   ├── engine.py        # DuckDB connection manager
│       │   └── schema.py        # Table definitions
│       ├── models/              # Pydantic request/response models
│       ├── routers/             # API route handlers
│       ├── services/
│       │   ├── ingestion.py     # Event validation + batch insert
│       │   ├── nl_to_sql.py     # OpenAI SQL generation + orchestration
│       │   ├── chart_config.py  # Chart type determination
│       │   └── sql_sandbox.py   # SQL validation + sandboxing
│       └── utils/
│           └── api_key.py       # Key generation + hashing
├── frontend/
│   └── src/
│       ├── api/client.ts        # API client
│       ├── stores/authStore.ts  # Auth state (Zustand)
│       ├── components/          # ChartRenderer, QueryBar, Layout
│       └── pages/               # Dashboard, Saved, Settings, Login
├── scripts/
│   ├── seed.py                  # Generate demo org + 15K events
│   └── run_dev.sh               # Start both servers
└── data/                        # DuckDB file (gitignored)
```
