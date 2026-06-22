import json
import logging
import httpx
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from app.config import settings

logger = logging.getLogger("audit_tool.narrator")

class _AuditJSONEncoder(json.JSONEncoder):
    """Handles non-serializable types that come back from Postgres (UUID, datetime, Decimal, etc.)."""
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def generate_narrative(findings: list[dict]) -> str | None:
    """
    Sends structured findings to a chosen AI provider (Gemini or Ollama) to generate a narrative.
    Returns the narrative string or None if the request fails.
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

    findings_json = json.dumps(simplified_findings, indent=2, cls=_AuditJSONEncoder)

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
    system_instruction = "You are a precise and factual compliance narration assistant. Never speculate or hallucinate."

    if settings.ai_provider.lower() == "gemini":
        if not settings.gemini_api_key:
            logger.error("GEMINI_API_KEY is not set.")
            return None
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "systemInstruction": {
                "parts": [
                    {"text": system_instruction}
                ]
            },
            "generationConfig": {
                "temperature": 0.2
            }
        }
        
        try:
            logger.info(f"Contacting Gemini at {url.split('?')[0]} using model {settings.gemini_model}...")
            response = httpx.post(url, json=payload, timeout=60.0)
            
            if response.status_code == 200:
                result = response.json()
                try:
                    return result["candidates"][0]["content"]["parts"][0]["text"].strip()
                except (KeyError, IndexError):
                    logger.error(f"Unexpected Gemini response format: {result}")
                    return None
            else:
                logger.warning(f"Gemini returned status code {response.status_code}: {response.text}")
                return None
        except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError) as e:
            logger.error(f"Failed to generate narrative from Gemini: {str(e)}")
            return None

    else:
        # Default to Ollama
        url = f"{settings.ollama_base_url.rstrip('/')}/api/generate"
        payload = {
            "model": settings.ollama_model,
            "prompt": prompt,
            "system": system_instruction,
            "options": {
                "temperature": 0.2,
                "num_ctx": 4096,
                "think": False 
            },
            "stream": False
        }

        try:
            logger.info(f"Contacting Ollama at {url} using model {settings.ollama_model}...")
            response = httpx.post(url, json=payload, timeout=300.0)
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                logger.warning(f"Ollama returned status code {response.status_code}: {response.text}")
                return None
        except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError) as e:
            logger.error(f"Failed to generate narrative from Ollama: {str(e)}")
            return None
