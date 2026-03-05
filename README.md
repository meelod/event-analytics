# Event Analytics Platform

A lightweight, open-source alternative to Mixpanel. Multi-tenant event analytics with natural language querying and automatic chart rendering. Built entirely for local use — no Docker, no external databases, no cloud infrastructure required.

## Architecture Overview

```
┌─────────────────── INGESTION PATH ────────────────────┐
│                                                        │
│  [SDK / curl]  ──X-API-Key──>  POST /events  ──>  DuckDB
│                                                        │
└────────────────────────────────────────────────────────┘

┌─────────────────── QUERY PATH ────────────────────────┐
│                                                        │
│  [Browser]  ──Session Cookie──>  POST /query           │
│                                    │                   │
│                                    v                   │
│                              GPT-4o: NL → SQL          │
│                                    │                   │
│                                    v                   │
│                              SQL Sandbox (4 layers)    │
│                                    │                   │
│                                    v                   │
│                              DuckDB: Execute query     │
│                                    │                   │
│                                    v                   │
│                              GPT-4o-mini: Chart config │
│                                    │                   │
│                                    v                   │
│                              React + Recharts: Render  │
│                                                        │
└────────────────────────────────────────────────────────┘
```

**Tech Stack:**
- **Backend:** Python 3.11, FastAPI, DuckDB (embedded analytical database)
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Recharts, Zustand
- **LLM:** OpenAI GPT-4o (SQL generation), GPT-4o-mini (chart configuration)
- **SQL Safety:** sqlglot for AST-level validation of LLM-generated queries

---

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

# 3. Seed demo data (creates org + 15K events across 7 event types)
python3 scripts/seed.py
# Save the API key that is printed - it's shown only once!

# 4. Start both servers
./scripts/run_dev.sh
```

Open http://localhost:5173, login with the API key from step 3.

> **Forgot your API key?** Click the ⚙ gear icon on the login page to enter developer mode — it lists all existing organizations and lets you log in with one click, no key needed.

### Running Servers Individually

```bash
# Backend only (port 8000)
cd backend && python3 -m uvicorn app.main:app --port 8000 --reload

# Frontend only (port 5173, proxies /api to backend)
cd frontend && npm run dev
```

### Try These Queries
- "Show daily active users for the last 30 days"
- "What are the top 5 events this week?"
- "Show conversion from signup to purchase by day"
- "What pages get the most views?"
- "Show hourly event volume for today"
- "How many users signed up this month?"

---

## Data Flow (End-to-End)

### 1. Event Ingestion
```
Client sends event → API key validated (SHA-256 hash lookup)
  → org_id resolved from key → Event validated (Pydantic)
  → UUID generated, timestamp defaulted → Batch INSERT into DuckDB
```

Events are the raw data. Each event has:
- `event_name` (e.g., "page_view", "signup", "purchase")
- `distinct_id` (user identifier, e.g., "user-123")
- `properties` (JSON object with arbitrary key-value pairs)
- `org_id` (automatically set from the authenticated API key — never from user input)
- `timestamp` (client-provided or server-defaulted to now)

### 2. Natural Language Query
```
User types question → POST /api/v1/query
  → Fetch real event names + property keys from DuckDB (context injection)
  → Build system prompt with schema + event context + safety rules
  → GPT-4o generates SQL (temperature=0 for determinism)
  → SQL Sandbox validates: regex → AST → org_id check → LIMIT
  → DuckDB executes the validated SQL
  → GPT-4o-mini determines chart type from question + results
  → Return: { generated_sql, data, chart_config, execution_time_ms }
```

### 3. Chart Rendering
```
Frontend receives response → ChartRenderer reads chart_config JSON
  → Config specifies: chart_type, x_axis, y_axis, series[]
  → Object lookup maps chart_type → Recharts component
  → Renders: LineChart, BarChart, AreaChart, PieChart, single number, or table-only
```

### 4. Saving a Visualization
```
User clicks "Save" → POST /api/v1/visualizations
  → Stores snapshot: question, SQL, result data, chart config
  → Reload is instant (no LLM call, renders from cached data)
  → Trade-off: data may become stale, but saves LLM tokens
```

---

## Key Services (Backend)

### `services/nl_to_sql.py` — NL-to-SQL Pipeline
The core intelligence of the system. Orchestrates the full query flow:
1. **Context injection** (`get_org_context()`): Queries real event names and property keys from DuckDB and appends them to the LLM prompt. This prevents the LLM from hallucinating event names that don't exist in the data.
2. **SQL generation** (`generate_sql()`): Calls GPT-4o with a detailed system prompt containing the full schema, 13 DuckDB-specific rules, and the org's actual event catalog. Temperature=0 for deterministic output.
3. **Orchestration** (`generate_and_execute_query()`): Generate SQL → validate in sandbox → execute against DuckDB → get chart config → return everything.

### `services/sql_sandbox.py` — SQL Safety (Defense in Depth)
LLM-generated SQL is **untrusted input**. The sandbox applies four validation layers:

| Layer | What it catches | How |
|-------|----------------|-----|
| 1. Regex blocklist | INSERT, DROP, COPY, file functions, ATTACH | Pattern matching on raw SQL |
| 2. AST parsing | Multiple statements, non-SELECT queries | sqlglot parses SQL into an AST |
| 3. Org ID check | Missing tenant isolation filter | String check for org_id in SQL |
| 4. LIMIT enforcement | Unbounded result sets | Appends `LIMIT 10000` if missing |

### `services/chart_config.py` — Chart Type Determination
Uses GPT-4o-mini (cheaper model, simpler task) to determine the best visualization:
- Sends the question, SQL, column names, and 3 sample rows
- Returns a JSON config matching the ChartRenderer's expected format
- Guidelines: time series → line, categorical → bar, proportions → pie, single value → number, raw listings → table

### `services/ingestion.py` — Event Ingestion
Validates and inserts events with a **partial success pattern**: if one event in a batch fails validation, the rest still get inserted. Uses `executemany` for batch efficiency.

### `services/seeding.py` — Demo Data Generation
Generates realistic randomized events callable from the backend API (used by the developer mode "Seed Demo Data" button in Settings). Same 7 event types, weights, and property distributions as the CLI seed script. Inserts in batches of 1000 and returns the count + distribution breakdown.

### `db/engine.py` — DuckDB Connection Manager
Manages the single DuckDB connection with:
- **asyncio.Lock** for write serialization (DuckDB's single-writer constraint)
- **Cursor-based reads** that leverage DuckDB's MVCC (reads never block writes)
- **executemany** for batch inserts (one round-trip for N events)

---

## Architecture Decisions & Trade-offs

### Why DuckDB?
DuckDB is an embedded columnar analytical database — think "SQLite for analytics":
- **No Docker/infrastructure required** — it's a pip install, satisfying the local-only requirement
- **Columnar storage** — optimized for the aggregation queries this platform runs (COUNT, GROUP BY, date_trunc)
- **Standard SQL** — LLM-generated queries work naturally
- **MVCC concurrency** — reads never block writes within the same process
- **Trade-off**: Single-writer constraint means writes are serialized via asyncio.Lock. Fine for this use case (event ingestion isn't high-throughput for a local tool).

### Why Two LLM Calls?
Splitting SQL generation (GPT-4o) and chart configuration (GPT-4o-mini):
- **Accuracy**: SQL generation is the harder task; using the best model improves reliability
- **Cost**: Chart config is simple pattern matching; using mini saves ~10x per call
- **Reliability**: A single prompt producing both SQL and chart JSON is more fragile
- **Trade-off**: Two API calls add ~1-2s latency. Acceptable for an analytics dashboard.

### Why No ORM?
- DuckDB has excellent Python SQL support with parameterized queries
- ORMs add abstraction overhead without benefit for simple CRUD + raw analytics queries
- The SQL sandbox needs to work with raw SQL strings anyway
- Direct SQL is more idiomatic for analytical workloads

### Why API Key for Login?
- This is a local-only tool, not a SaaS with user accounts
- The API key already exists for ingestion auth — reusing it avoids managing a second credential
- Avoids complexity of password hashing, reset flows, etc.
- **Trade-off**: If the key leaks, both ingestion AND dashboard access are compromised

### Saved Visualization Snapshots
- Saved visualizations store a **snapshot** of the data at save time
- Reloading is instant (no LLM call or query needed)
- **Trade-off**: Data may become stale. In production you'd add a "refresh" button that re-runs the query.

---

## Multi-Tenant Isolation

Four layers ensure one org can never access another's data:

1. **Ingestion**: `org_id` is set from the authenticated API key, never from user input
2. **Query generation**: The system prompt hardcodes `WHERE org_id = '{org_id}'` in every SQL query
3. **SQL sandbox**: Verifies the org_id string appears in the generated SQL before execution
4. **Session auth**: The org is resolved from the session token in the database, not from request parameters

---

## Authentication

Two auth mechanisms for two different consumers, plus developer convenience:

| Mechanism | Used By | How It Works |
|-----------|---------|--------------|
| **API Key** (`X-API-Key` header) | SDKs, curl, scripts | Key is `ea_live_<64 hex chars>`. Stored as SHA-256 hash. Validated by hashing the incoming key and looking up the hash. |
| **Session Cookie** (HttpOnly) | Dashboard UI | Login with API key → creates session row in DB → sets HttpOnly cookie (24h expiry). Cookie is validated on each request by looking up the token with expiry check. |
| **Dev Login** (gear icon) | Developer convenience | Bypasses API key — lists all orgs and creates a session directly by org ID. API keys are hashed and unrecoverable, so this provides a way to log in without remembering them. |

---

## Developer Mode

Developer mode provides two conveniences for local development:

### Quick Login (Login Page ⚙)
Click the gear icon on the login page to reveal a list of all existing organizations. Click any org to log in instantly — no API key needed. This exists because API keys are SHA-256 hashed in the database and can't be retrieved after creation.

### Seed Demo Data (Settings Page)
On the Settings page, toggle "Developer mode" to reveal a "Seed Demo Data" button. Clicking it generates 1,000 randomized events (7 types, realistic properties, 30 days of history) directly into the current org's data. The success response shows the count and per-event-type distribution. Head to the Dashboard to immediately query the new data.

### Send Event (Settings Page)
Developer mode also reveals a "Send Event" form. Click any of the 7 event type tags (page_view, signup, login, etc.) to select it — properties auto-fill with realistic defaults matching the seed data. Property values are clickable tags (e.g., browser: Chrome / Firefox / Safari / Edge), while numeric fields like `amount` use a text input. Click "Send Event" to insert a single event into the current org's data via the same `POST /events` endpoint used by SDKs.

> In production, you'd gate these endpoints behind an environment flag or remove them entirely.

---

## API Reference

### Organization Management

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/orgs` | None | Create organization + API key |

**Request:** `{ "name": "Acme Corp", "slug": "acme" }`
**Response:** `{ "id": "uuid", "name": "Acme Corp", "slug": "acme", "api_key": "ea_live_...", "created_at": "..." }`

### Authentication

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/auth/login` | None | Login with API key (sets session cookie) |
| `GET` | `/api/v1/auth/me` | Session | Get current org info |
| `POST` | `/api/v1/auth/logout` | None | Clear session cookie |
| `GET` | `/api/v1/auth/dev/orgs` | None | List all organizations (dev mode) |
| `POST` | `/api/v1/auth/dev/login` | None | Login by org ID without API key (dev mode) |

### Event Ingestion

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/events` | API Key or Session | Ingest single event |
| `POST` | `/api/v1/events/batch` | API Key | Ingest batch (up to 1000) |
| `POST` | `/api/v1/events/seed` | Session | Seed randomized demo data (dev mode) |

### Querying

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/query` | Session | Natural language → SQL → data + chart config |

### Saved Visualizations

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/v1/visualizations` | Session | List saved visualizations |
| `POST` | `/api/v1/visualizations` | Session | Save a visualization |
| `GET` | `/api/v1/visualizations/:id` | Session | Get saved visualization |
| `DELETE` | `/api/v1/visualizations/:id` | Session | Delete visualization |

### Example Requests

**Single event:**
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

**Batch (up to 1000 events):**
```bash
curl -X POST http://localhost:8000/api/v1/events/batch \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{
    "events": [
      {"event": "signup", "distinct_id": "user-1"},
      {"event": "purchase", "distinct_id": "user-2", "properties": {"amount": 99.99}}
    ]
  }'
```

**NL query:**
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -H "Cookie: session=YOUR_SESSION_TOKEN" \
  -d '{"question": "Show daily active users for the last 30 days"}'
```

**Dev login (no API key):**
```bash
# List all orgs
curl http://localhost:8000/api/v1/auth/dev/orgs

# Login by org ID
curl -X POST http://localhost:8000/api/v1/auth/dev/login \
  -H "Content-Type: application/json" \
  -d '{"org_id": "ORG_UUID_HERE"}'
```

**Seed demo data (requires session):**
```bash
curl -X POST http://localhost:8000/api/v1/events/seed \
  -H "Content-Type: application/json" \
  -H "Cookie: session=YOUR_SESSION_TOKEN" \
  -d '{"count": 1000, "days_back": 30}'
```

---

## Database Schema

Five tables in DuckDB:

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `organizations` | Tenant registry | id (UUID), name, slug (unique) |
| `api_keys` | Auth for ingestion | key_hash (SHA-256), key_prefix, org_id, is_active |
| `events` | Analytics data (append-only, no PK) | org_id, event_name, distinct_id, timestamp, properties (JSON) |
| `saved_visualizations` | Saved query result snapshots | org_id, nl_question, generated_sql, result_data (JSON), chart_config (JSON) |
| `sessions` | Dashboard auth state | org_id, token (unique), expires_at |

**Design note:** The `events` table has no primary key. It's append-only by design — columnar databases optimize for bulk inserts and analytical reads, not row-level updates. The lack of a PK avoids index maintenance overhead.

---

## Frontend Architecture

### State Management (Zustand)
- `authStore.ts`: Global auth state (orgId, orgName, isLoading)
- Actions: `login()`, `devLogin()`, `logout()`, `checkSession()`
- Session check on app mount prevents login page flash on refresh
- No Redux boilerplate — Zustand uses a single `create()` call

### Config-Driven Chart Rendering
`ChartRenderer.tsx` is a pure presentation component:
- Backend decides WHAT to render (chart type, axes, series) via ChartConfig JSON
- Frontend just maps config to Recharts components
- Object lookup pattern (`{line: LineChart, bar: BarChart, ...}`) instead of switch statement
- Supports 6 chart types: line, bar, area, pie, number, table (skips chart, shows data only)

### Routing
- React Router v6 with nested routes
- `Layout` component renders sidebar + `<Outlet />` for active page
- `ProtectedRoute` wrapper redirects to login if no valid session
- Pages: Dashboard, Saved Visualizations, Settings

### API Client
- `api/client.ts`: Centralized fetch wrapper with `credentials: "include"` for cookies
- Every endpoint is a one-liner function calling the generic `request<T>()` helper
- Error handling extracts FastAPI's `{detail: "message"}` format

---

## Project Structure

```
event-analytics/
├── backend/
│   ├── requirements.txt            # Python dependencies
│   └── app/
│       ├── main.py                 # FastAPI app, lifespan, CORS config
│       ├── config.py               # Settings via pydantic-settings (.env)
│       ├── dependencies.py         # Auth dependencies (API key + session)
│       ├── db/
│       │   ├── engine.py           # DuckDB connection manager (write lock, MVCC reads)
│       │   └── schema.py           # CREATE TABLE DDL statements
│       ├── models/
│       │   ├── organization.py     # Org create/response models
│       │   ├── event.py            # Event + Seed request/response models
│       │   ├── query.py            # NL query request/response + ChartConfig
│       │   └── visualization.py    # Saved visualization CRUD models
│       ├── routers/
│       │   ├── organizations.py    # POST /orgs
│       │   ├── auth.py             # Login, logout, session check, dev login
│       │   ├── ingest.py           # Single + batch ingestion, seed endpoint
│       │   ├── query.py            # NL query endpoint
│       │   └── visualizations.py   # Saved visualizations CRUD
│       ├── services/
│       │   ├── ingestion.py        # Event validation + batch insert
│       │   ├── nl_to_sql.py        # GPT-4o SQL generation + orchestration
│       │   ├── chart_config.py     # GPT-4o-mini chart type determination
│       │   ├── sql_sandbox.py      # 4-layer SQL validation
│       │   └── seeding.py          # Demo data generation (dev mode)
│       └── utils/
│           └── api_key.py          # Key generation (ea_live_*) + SHA-256 hashing
├── frontend/
│   ├── package.json
│   ├── vite.config.ts              # Dev proxy: /api/* → localhost:8000
│   └── src/
│       ├── main.tsx                # Entry point (React + Router + Tailwind)
│       ├── App.tsx                 # Routes + ProtectedRoute auth guard
│       ├── api/client.ts           # Centralized fetch wrapper for all API calls
│       ├── stores/authStore.ts     # Zustand auth state (login, devLogin, logout)
│       ├── components/
│       │   ├── ChartRenderer.tsx   # Config-driven Recharts (line/bar/area/pie/number/table)
│       │   ├── QueryBar.tsx        # NL input + example question buttons
│       │   └── Layout.tsx          # Sidebar navigation + Outlet
│       └── pages/
│           ├── DashboardPage.tsx   # Query bar + chart + SQL preview + raw data + save
│           ├── LoginPage.tsx       # Login + org creation + dev quick login (⚙)
│           ├── SavedVisualizationsPage.tsx  # Browse + reload saved analytics
│           └── SettingsPage.tsx    # Org info + API docs + dev mode seed + send event
├── scripts/
│   ├── seed.py                     # CLI: generate org + events (--name, --slug, --events, --days)
│   └── run_dev.sh                  # Start backend + frontend together
├── data/                           # DuckDB file (gitignored)
├── .env.example                    # Environment variable template
└── .gitignore
```

---

## Seed Data

Two ways to seed demo data:

### CLI (scripts/seed.py)

```bash
# Default: creates "Demo Organization" with 15K events over 30 days
python3 scripts/seed.py

# Custom org with custom parameters
python3 scripts/seed.py --name "Acme Corp" --slug acme --events 5000 --days 60
```

| Flag | Default | Description |
|------|---------|-------------|
| `--name` | "Demo Organization" | Organization display name |
| `--slug` | "demo" | URL-friendly identifier (must be unique) |
| `--events` | 15000 | Number of events to generate |
| `--days` | 30 | Days of history to spread events across |

### UI (Settings → Developer Mode)

Toggle developer mode in Settings, then click "Seed Demo Data" to generate 1,000 events for the current org directly from the browser. No terminal needed.

### Event Types and Weights

| Event | Weight | Example Properties |
|-------|--------|--------------------|
| page_view | 50 | page, referrer, browser |
| button_click | 30 | button_id, page |
| login | 20 | method (email/google/github) |
| feature_used | 15 | feature (dashboard/export/api) |
| signup | 8 | plan (free/pro), source |
| error | 5 | error_code, page |
| purchase | 3 | amount, plan, currency |

Events use 200 synthetic user IDs and are distributed with a Gaussian bias toward business hours (peak at 1pm).
