# One-Person Tech Studio 🚀
> Three production-grade systems spanning AI governance, event-driven streaming reliability, and autonomous data contracts.

This studio repository houses three decoupled, production-grade technical products designed to solve operational bottlenecks in real-time streaming, modern data pipelines, and multi-tenant AI systems.

---

## Portfolio Overview

| System | Core Problem Addressed | Key Architecture & Stack | Verification Status |
| :--- | :--- | :--- | :--- |
| **[Solo AI Engine](./solo-ai-engine/)** | Multi-tenant LLM token abuse, lack of auditability, and vendor lock-in | FastAPI, SQLite, Token Bucket Algorithms, Groq Cloud, Tailwind UI | **Production Ready** |
| **[StreamPulse](./streampulse/)** | Telemetry alert fatigue, high throughput ingestion, and delayed incident triage | Redpanda (C++ Kafka), Redis Rolling Windows, $Z \ge 3.5\sigma$ Gating, SSE, Groq Triage | **Production Ready** |
| **[SchemaSentinel](./schemasentinel/)** | Silent data pipeline failures and breaking schema drift in analytical warehouses | DuckDB, Pydantic v2, YAML Contracts, Self-Healing SQL Views, Typer/Rich CLI, GitHub Actions | **Production Ready** |

---

## 1. Solo AI Engine ⚡
**Multi-Tenant AI Governance Platform & Inference Gateway**

Solo AI Engine provides a centralized, secure API gateway and management dashboard for multi-tenant organizations interacting with large language models. It enforces rate limits, manages token budgets per tenant, and logs auditable analytics.

* **Tenant Isolation**: Deterministic token-bucket rate limiting per API key to protect downstream model quotas.
* **Low-Latency Inference**: Direct provider abstraction over Groq API with streaming responses.
* **Usage Telemetry**: In-memory and persisted SQLite usage tracking for prompt tokens, completion tokens, and dollar expenditures.
* **Console Dashboard**: Zero-framework, responsive client interface for real-time tenant provisioning and quota monitoring.

```bash
cd solo-ai-engine
python -m venv venv && .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

---

## 2. StreamPulse 📊
**High-Throughput Telemetry Broker & Automated Incident Triage Engine**

StreamPulse tackles alert fatigue in distributed architectures. It ingests thousands of telemetry events per second, calculates real-time rolling statistical distributions in Redis, filters noise using standard deviation thresholds, and routes true anomalies to an LLM triage engine.

* **Distributed Ingestion**: Redpanda streaming cluster handling high-volume event ingestion without JVM overhead.
* **Statistical Filtering**: Redis Sorted Sets (`ZSET`) maintaining sliding 30-second windows; only telemetry events breaching $Z \ge 3.5\sigma$ trigger alert routing.
* **Hybrid Diagnostic Engine**: Automated triage combining semantic LLM diagnostics with local heuristic rule fallbacks for sub-second MTTR.
* **Live Incident Streaming**: Server-Sent Events (SSE) pipe pushing critical incidents to an operations HUD.

```bash
cd streampulse
docker compose up -d
python producer.py --rate 100 --anomaly-interval 20
python consumer.py
uvicorn api.main:app --reload --port 8001
```

---

## 3. SchemaSentinel 🛡️
**Autonomous Data Contracts & Self-Healing Analytical Engine**

SchemaSentinel prevents pipeline breakage caused by upstream schema alterations (column renaming, type drift, null injections). It validates batch datasets against declarative YAML contracts using DuckDB and dynamically generates self-healing SQL migration views.

* **Vectorized Analytical Validation**: DuckDB in-memory validation engine executing type checks, regex matching, and custom SQL rules directly on CSV/Parquet files without loading data into memory.
* **Self-Healing Synthesis**: Identifies schema drift (e.g., `user_uuid` replacing `customer_id`), binds missing columns, sanitizes uncontracted enums, and synthesizes non-destructive SQL adapter views (`CREATE VIEW v_dataset_healed`).
* **CI/CD Quality Gate**: Command-line interface (`schemasentinel test`) and GitHub Actions workflow to block breaking schema migrations prior to pull request merges.

```bash
cd schemasentinel
python data/generate_samples.py
python cli/main.py test --contract contracts/orders_v1.yaml --data data/orders_clean.csv
python cli/main.py heal --contract contracts/orders_v1.yaml --data data/orders_corrupted.csv
pytest -v
```

---

## Studio Directory Layout

```text
solopreneur/
├── README.md                      # Studio portfolio hub
├── solo-ai-engine/                # Product #1: AI Gateway & Governance
│   ├── app/
│   ├── database/
│   ├── static/
│   └── main.py
├── streampulse/                   # Product #2: Real-Time Event Analytics
│   ├── docker-compose.yml
│   ├── producer.py
│   ├── consumer.py
│   └── api/
└── schemasentinel/                # Product #3: Data Contracts & Remediation
    ├── contracts/
    ├── core/
    ├── cli/
    ├── tests/
    └── .github/workflows/
```