import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

# Allow the Vite dev server to call the API without CORS errors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
