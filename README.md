# Internal Audit App

Internal Audit App is a full-stack auditing platform for running rule-based internal compliance checks, generating audit reports, and supporting policy analysis workflows.

## Repository Structure

- `audit-tool/` - FastAPI backend for audit execution, policy endpoints, and report generation
- `audit-dashboard/` - React + Vite frontend dashboard
- `rules/` (under `audit-tool/`) - YAML audit rules used by the engine
- `Dockerfile` / `docker-compose.yml` - Containerized runtime for API and Qdrant
- `Jenkinsfile` - CI/CD pipeline that builds, pushes, and deploys the app

## Tech Stack

- Backend: FastAPI, SQLAlchemy, Supabase/PostgreSQL integrations
- Frontend: React, Vite, Tailwind CSS
- AI/Policy: Ollama integration and vector search with Qdrant
- Deployment: Docker, Jenkins, Azure Container Registry, Azure Container Apps

## Local Development

### 1) Backend setup

```bash
cd audit-tool
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend runs on `http://localhost:8000`.

### 2) Frontend setup

```bash
cd audit-dashboard
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`.

### 3) Docker compose (backend + Qdrant)

From repository root:

```bash
docker compose up --build
```

## Key API Endpoints

- `GET /health` - Service and DB health check
- `GET /audits/run` - Run all configured audit rules
- `GET /audits/{rule_id}` - Run one audit rule
- `GET /audits/report` - Generate full audit report
- Policy routes are available under `/policies`

## Testing

Run backend tests:

```bash
cd audit-tool
pytest
```

## Deployment (Jenkins VM + Azure)

This project is configured for deployment through a Jenkins pipeline running on a VM, with containers hosted in Azure:

1. Jenkins checks out the latest code.
2. Jenkins builds a Docker image tagged with the short Git commit hash.
3. Jenkins logs in to **Azure Container Registry (ACR)** and pushes the image.
4. Jenkins authenticates to Azure using a service principal.
5. Jenkins updates the **Azure Container App** with the new image and environment variables.

Pipeline config is defined in `/Jenkinsfile` and currently references:

- ACR: `internalauditreg.azurecr.io`
- Image: `internal-audit-app`
- Resource Group: `internal-audit-app`
- Container App: `internal-audit-app`

## Notes

- Root `main.py` is intentionally a pointer; the active backend entrypoint is `audit-tool/app/main.py`.
- Ensure required environment files and secrets are configured in Jenkins credentials before deployment.