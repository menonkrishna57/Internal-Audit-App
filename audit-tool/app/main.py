import logging
from fastapi import FastAPI
from app.routes import audits

# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("audit_tool.main")

app = FastAPI(
    title="Bank Operational Audit Tool",
    description="Backend service that runs automated audit rules against internal databases and generates narrated compliance reports.",
    version="0.1.0"
)

# Register routes
app.include_router(audits.router, prefix="/audits")

@app.get("/health")
def health_check():
    """Confirms the API engine is alive."""
    return {"status": "healthy", "service": "bank-audit-tool"}

@app.get("/")
def home():
    """Welcome page redirect or metadata response."""
    return {
        "message": "Welcome to the Bank Operational Audit Tool API",
        "docs_url": "/docs",
        "endpoints": {
            "health": "/health",
            "run_audits": "/audits/run",
            "audit_report": "/audits/report",
            "single_audit": "/audits/{rule_id}"
        }
    }
