import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import audits
from app.routes import policies

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
app.include_router(policies.router, prefix="/policies")

from sqlalchemy import text
from app.db import get_engine

import os
from fastapi.staticfiles import StaticFiles

@app.get("/health")
def health_check():
    """Confirms the API engine is alive and checks DB connection."""
    db_status = "error"
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        
    return {
        "status": "healthy", 
        "service": "bank-audit-tool",
        "db_status": db_status
    }

# Serve the frontend Dashboard
dist_path = os.path.join(os.path.dirname(__file__), "..", "..", "audit-dashboard", "dist")
if os.path.isdir(dist_path):
    app.mount("/", StaticFiles(directory=dist_path, html=True), name="frontend")
else:
    @app.get("/")
    def home():
        return {
            "message": "Welcome to the Bank Operational Audit Tool API",
            "docs_url": "/docs",
            "endpoints": {
                "health": "/health",
                "run_audits": "/audits/run",
                "audit_report": "/audits/report",
                "single_audit": "/audits/{rule_id}"
            },
            "note": "Frontend build not found. Run 'npm run build' in audit-dashboard."
        }
