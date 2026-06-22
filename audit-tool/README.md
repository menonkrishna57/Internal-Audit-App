# Bank Operational Audit Tool

A FastAPI + SQLAlchemy backend that runs YAML-defined audit rules against a Supabase Postgres database and summarizes findings using a local Ollama model (phi4-mini).

## Setup
1. Copy `.env.example` to `.env` and fill in the values.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## Endpoints
- `GET /health` - API health check
- `GET /audits/run` - Runs all YAML audit rules and returns JSON output
- `GET /audits/{rule_id}` - Runs a specific audit rule
- `GET /audits/report` - Runs all rules and generates an HTML report with Ollama narration (optional fallback if Ollama is offline)
