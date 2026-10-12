# SchemaSentinel 🛡️
> Autonomous Data Contract Enforcement & Self-Healing Analytical Engine

SchemaSentinel enforces declarative data contracts directly on raw analytical feeds (CSV, Parquet, JSON) using DuckDB. When breaking schema drift, type divergence, or data corruption is detected, it acts as a CI/CD gatekeeper and automatically synthesizes self-healing SQL migration views to keep downstream pipelines operational.

## Architecture

```text
[Incoming Feeds] ──▶ [SchemaSentinel (DuckDB Engine)]
                              │
               ┌──────────────┴──────────────┐
               ▼                             ▼
       [Contract Pass]               [Breach / Drift]
               │                             │
       Auto-Ingest Stream                    ├──▶ [CI/CD Gate: Fail PR]
                                             └──▶ [Self-Healing Engine]
                                                       │
                                                       ▼
                                            [DuckDB Adapter View (.sql)]
```

* **Validation Engine**: In-memory analytical checks powered by **DuckDB** (executes type checks, nullability tests, regex rules, and relational assertions without loading datasets into Pandas).
* **Declarative Contracts**: YAML specifications declaring column definitions, value domains, regex patterns, and custom SQL assertions.
* **Autonomous Remediation**: AST and schema diff analyzer that maps renamed attributes (`user_uuid` ➔ `customer_id`), coerces data types, sanitizes invalid enums, and synthesizes non-destructive SQL views (`v_<dataset>_healed`).
* **CI/CD Quality Gate**: Pre-merge testing gate via GitHub Actions to block breaking upstream schema migrations.

---

## Quickstart

### 1. Environment Setup
```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Generate Synthetic Datasets
Generate clean baseline data and a corrupted, schema-drifted batch:
```bash
python data/generate_samples.py
```

### 3. Inspect & Enforce Contracts (CLI)
Validate the clean dataset:
```bash
python cli/main.py test --contract contracts/orders_v1.yaml --data data/orders_clean.csv
```

Detect contract breaches on drifted data:
```bash
python cli/main.py test --contract contracts/orders_v1.yaml --data data/orders_corrupted.csv
```

### 4. Synthesize Self-Healing Adapter
Generate and verify a self-healing DuckDB SQL view:
```bash
python cli/main.py heal --contract contracts/orders_v1.yaml --data data/orders_corrupted.csv
```

### 5. Run Regression Test Suite
```bash
pytest -v
```