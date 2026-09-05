# Sanger Trace Trimmer

> **Domain:** Clinical Decision Support & Biomedical Computing
> **Reference Guidelines & Standards:** Standard Clinical Formulations & ISO/IEC Quality Frameworks

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

Sanger AB1 quality trim via Mott algorithm with Q20/Q30 quality scoring, ambiguous call rate analysis, and vector screen stub. Includes stdlib CSV parser/mapper with batch processing and single lookup capabilities.

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Analytical Functions

- **`lookup(query)`** — Single term lookup using token overlap + substring scoring (no external dependencies). Returns top hits with relevance scores.
- **`process_csv(inp, out)`** — Batch processes CSV files, running lookup on each row against a query column. Outputs enriched results.
- **`build_parser()`** — Constructs the CLI argument parser with subcommands.
- **`main(argv)`** — CLI entry point for `sanger_trim` module.

---

## 💻 Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/sanger-trace-trimmer.git
cd sanger-trace-trimmer

# Install dependencies
pip install -e .

# For development (includes pytest)
pip install -e ".[dev]"
```

---

## 🚀 CLI Quickstart & Usage

### 1. Single Lookup
```bash
python -m sanger_trim single creatinine
```

### 2. Batch CSV Processing
```bash
python -m sanger_trim batch --input sample.csv --output results.csv
```

### 3. Supervisor CLI (Enterprise Features)
```bash
# Run a single audit task
python cli.py audit --task-id TASK-001 --primary 28.5 --secondary 14.2

# Batch process records
python cli.py batch -i sample.csv -o results.csv

# Verify audit trail integrity
python cli.py verify-audit

# Start FastAPI server
python cli.py serve --host 127.0.0.1 --port 8000
```

### Parameter Reference
- `--task-id`: Unique task / case identifier
- `--target`: Entity, patient key, or genomic target
- `--primary`: Primary domain measurement or score
- `--secondary`: Secondary kinetic or confidence score
- `--critical`: Emergency escalation flag
- `--status`: Status code or phenotype descriptor

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Air-Gapped LLM Reasoning Adapter:** Agnostic integration for local Ollama instances (`llama3`, `mistral`), Claude 3.5 Sonnet, GPT-4o, and deterministic test mocks.
* **FastAPI & Prometheus Telemetry:** Exposes OpenAPI 3.1 REST endpoints and operational Prometheus metrics (`/metrics`).

### Security Configuration

**IMPORTANT:** Set a strong random secret for the audit trail in production:

```bash
# Generate a secure key
python -c "import secrets; print(secrets.token_hex(32))"

# Set via environment variable
export AUDIT_SECRET_KEY="your-generated-key"
```

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py 1000
```

---

## 🐳 Container Deployment

```bash
# Build and run with Docker Compose
AUDIT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))") docker-compose up -d

# Or build manually
docker build -t sanger-trace-trimmer .
docker run -p 8000:8000 -e AUDIT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))") sanger-trace-trimmer
```

---

## 📁 Project Structure

```
sanger-trace-trimmer/
├── agents/                 # Enterprise agent framework
│   ├── api.py             # FastAPI REST endpoints
│   ├── base.py            # PHI guard, HMAC audit trail
│   ├── models.py          # Pydantic data models
│   ├── supervisor.py      # Multi-agent orchestrator
│   ├── workers.py         # Specialized evaluation workers
│   └── ...
├── tests/                 # Test suite
├── cli.py                 # Enterprise CLI entry point
├── sanger_trim.py         # Core lookup & CSV processing
├── simulator.py           # Load testing simulator
├── pyproject.toml         # Package manifest
└── Dockerfile             # Container build config
```

---

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.
