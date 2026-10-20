# Solo AI Engine — Developer Starter Kit (v1.3.0)

A production-grade, multi-tenant AI gateway boilerplate built with FastAPI, Groq, SQLAlchemy (Async), and Docker. Designed to eliminate 40+ hours of backend plumbing for developers building commercial AI applications, SaaS platforms, and agency automation workflows.

---

## ⚡ 60-Second Quickstart

### Automated Setup (Windows PowerShell)
Run the automated installation script from the project root:

```powershell
.\setup.ps1
```

This will automatically create a virtual environment, install locked dependencies, generate your `.env` configuration, and run the automated test suite.

### Manual Setup (Cross-Platform)

1. **Initialize Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. **Configure Environment:**
   ```bash
   cp .env.example .env
   ```
   Add your `GROQ_API_KEY` and set your secure `MASTER_ADMIN_KEY`.

3. **Verify the Installation:**
   ```bash
   pytest -v
   ```

4. **Boot the Gateway:**
   ```bash
   uvicorn main:app --reload --port 8000
   ```
   Access the Studio Dashboard at `http://localhost:8000` and interactive API docs at `http://localhost:8000/docs`.

---

## 📦 What Is Included

### 1. Multi-Tenant Gateway & Quota Governance
* **Constant-Time SHA-256 Key Hashing:** Raw API keys are never stored in plain text.
* **Per-Tenant Quota Gating (HTTP 429):** Pre-inference request evaluation that halts runaway clients and protects upstream LLM credits.
* **Database Isolation:** Tenant datasets and agent jobs are strictly scoped by organization ID.

### 2. High-Throughput Inference Layer
* **Low-Latency LLM Engine:** Native Groq integration supporting Llama 3 models.
* **Strict Schema Enforcement:** Automatic Pydantic model serialization preventing schema drift and malformed JSON responses.
* **Real-Time Token Streaming:** Server-Sent Events (SSE) route (`/api/v1/stream-analysis`) for instant ChatGPT-style token rendering.

### 3. Decoupled Asynchronous Agent Workers
* **Background Task Dispatch:** Non-blocking job submission (`POST /api/v1/jobs/submit` ➔ `202 Accepted`).
* **Tool-Reasoning Loop:** ReAct reasoning execution with polling status endpoints (`GET /api/v1/jobs/{job_id}`).

### 4. Zero-Dependency Executive PDF Engine
* **CSS Print Media Pipeline:** Jinja2 template compiling structured JSON into clean executive PDF reports via native browser print CSS—zero headless Chrome or heavy Docker browser containers required.

### 5. Automated Alerting & Operations
* **Async Webhook Dispatcher:** Non-blocking HTTP notification service delivering structured alert cards directly to Discord or Slack.

### 6. Production DevOps Harness
* **Docker Compose:** Multi-stage container deployment with SQLite database volume mounting.
* **GitHub Actions CI/CD:** Ready-to-use pipeline (`.github/workflows/ci.yml`) enforcing multi-tenant isolation tests on every push.

---

## 🛠️ Project Structure

```text
solo-ai-engine/
├── .env.example              # Sample environment template
├── setup.ps1                 # Windows 1-click bootstrap script
├── Dockerfile                # Production container spec
├── docker-compose.yml        # Container orchestration & volume mounts
├── requirements.txt          # Pinned dependencies
├── main.py                   # FastAPI routing, auth dependencies & endpoints
├── database.py               # Async SQLAlchemy models & engine configuration
├── tools.py                  # Agent reasoning tools & calculator functions
├── test_main.py              # Pytest test suite (isolation & lifecycle)
└── templates/
    └── index.html            # Dark-mode dashboard & quota monitor
```

---

## 🚢 Deployment Guide

### Deploying with Docker Compose
```bash
docker compose up -d --build
```
Inspect logs:
```bash
docker compose logs -f
```

### Environment Variables Reference
| Variable | Description | Default |
| :--- | :--- | :--- |
| `GROQ_API_KEY` | Your active Groq API Key | *Required* |
| `MASTER_ADMIN_KEY` | Admin token for tenant provisioning | `dev_secret_key_123` |
| `DATABASE_URL` | Async SQLite database path | `sqlite+aiosqlite:///./studio.db` |
| `DISCORD_SLACK_WEBHOOK_URL`| Target URL for incident/run webhooks | *Optional* |

---

## 📄 Commercial License
You are granted a non-exclusive license to use this starter kit to build, deploy, and monetize unlimited client projects and commercial SaaS applications. Redistribution or resale of this source code repository as a competing boilerplate is prohibited.