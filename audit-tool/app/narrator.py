import json
import logging
import httpx
from app.config import settings

logger = logging.getLogger("audit_tool.narrator")

def generate_narrative(findings: list[dict]) -> str | None:
    """
    Sends structured findings to a local Ollama model to generate a narrative.
    Returns the narrative string or None if the request fails or Ollama is offline.
    """
    if not findings:
        return "No findings were identified during this audit run."

    # Filter out findings detail to keep the context size manageable
    # We want rule_id, title, severity, finding_count, and brief summaries of findings if any
    simplified_findings = []
    for f in findings:
        simplified_findings.append({
            "rule_id": f.get("rule_id"),
            "title": f.get("title"),
            "severity": f.get("severity"),
            "finding_count": f.get("finding_count", 0),
            "findings_sample": f.get("findings", [])[:5]  # Limit to first 5 items to avoid blowing up context
        })

    findings_json = json.dumps(simplified_findings, indent=2)

    prompt = f"""You are a senior compliance analyst summarizing internal bank audit findings.

INSTRUCTIONS:
- Summarize the findings below for inclusion in a formal audit report.
- Stay strictly factual. Only reference employee names, account IDs, departments, dates, and figures that appear in the data.
- Do NOT invent statistics, speculate about intent, or add information not present in the findings.
- Group your summary by rule category.
- Write 2-4 sentences per category.
- Use a professional, neutral tone appropriate for a board-level report.

FINDINGS DATA:
{findings_json}
"""

    url = f"{settings.ollama_base_url.rstrip('/')}/api/generate"
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "system": "You are a precise and factual compliance narration assistant. Never speculate or hallucinate.",
        "options": {
            "temperature": 0.2
        },
        "stream": False
    }

    try:
        logger.info(f"Contacting Ollama at {url} using model {settings.ollama_model}...")
        # Use a timeout (e.g. 30s) to avoid hanging indefinitely if Ollama is slow/offline
        response = httpx.post(url, json=payload, timeout=45.0)
        
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "").strip()
        else:
            logger.warning(f"Ollama returned status code {response.status_code}: {response.text}")
            return None
    except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError) as e:
        logger.error(f"Failed to generate narrative from Ollama: {str(e)}")
        return None
