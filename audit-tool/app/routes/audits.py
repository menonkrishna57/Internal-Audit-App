import datetime
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import Connection

from app.db import get_connection
from app.engine import load_rules, execute_rule
from app.narrator import generate_narrative

logger = logging.getLogger("audit_tool.routes")

router = APIRouter()

# Resolve templates directory relative to this file
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@router.get("/run")
def run_all_audits(connection: Connection = Depends(get_connection)):
    """Runs all registered YAML audit rules and returns raw findings in JSON format."""
    rules = load_rules()
    if not rules:
        return {
            "executed_at": datetime.datetime.utcnow().isoformat(),
            "results": [],
            "message": "No rules found to execute."
        }

    results = []
    for rule in rules:
        res = execute_rule(rule, connection)
        results.append(res)

    return {
        "executed_at": datetime.datetime.utcnow().isoformat(),
        "results": results
    }

@router.get("/report", response_class=HTMLResponse)
def get_audit_report(
    request: Request,
    format: str = Query("html", regex="^(html|json)$"),
    connection: Connection = Depends(get_connection)
):
    """
    Runs all audit rules, invokes Ollama for findings narration,
    and returns either an HTML report or raw JSON.
    """
    rules = load_rules()
    results = []
    for rule in rules:
        res = execute_rule(rule, connection)
        results.append(res)

    # Invoke narrative generation
    # It must run after SQL rules execute, on their structured output
    # Fallback to None if Ollama is offline (handled gracefully in UI)
    narrative = generate_narrative(results)

    report_data = {
        "executed_at": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "results": results,
        "narrative": narrative
    }

    if format == "json":
        return report_data

    # Return HTML response using Jinja2
    return templates.TemplateResponse(
        "audit_report.html",
        {
            "request": request,
            "report": report_data
        }
    )

@router.get("/{rule_id}")
def run_single_audit(rule_id: str, connection: Connection = Depends(get_connection)):
    """Runs a single YAML audit rule matching the specified rule ID."""
    rules = load_rules()
    target_rule = None
    for rule in rules:
        if rule.get("id") == rule_id:
            target_rule = rule
            break

    if not target_rule:
        raise HTTPException(status_code=404, detail=f"Rule with ID '{rule_id}' not found.")

    res = execute_rule(target_rule, connection)
    return {
        "executed_at": datetime.datetime.utcnow().isoformat(),
        "result": res
    }
