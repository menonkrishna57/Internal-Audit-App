"""
rule_generator.py — AI-powered analysis of policy clauses to determine
whether they should update an existing YAML audit rule or generate a new one.

Pipeline per clause
-------------------
1. Embed the clause text (via vector_store).
2. Compare against existing rule title embeddings stored in Qdrant.
3. If similarity > UPDATE_THRESHOLD  → extract parameter changes, update YAML.
4. If similarity < UPDATE_THRESHOLD  → ask Gemini if the clause is auditable.
5. If auditable                      → ask Gemini to draft a new YAML rule.
6. Otherwise                         → SKIP.

The database schema is injected into every AI prompt so Gemini can produce
syntactically correct SQL that targets the real tables.
"""
from __future__ import annotations

import json
import logging
import re
import textwrap
from pathlib import Path
from typing import Any

import httpx
import yaml

from app.config import settings
from app.policy_engine.models import (
    ParameterChange,
    PolicyClause,
    RuleAction,
)
from app.policy_engine.vector_store import embed_texts, search_clauses

logger = logging.getLogger("audit_tool.policy_engine.rule_generator")

# ── Thresholds ────────────────────────────────────────────────────────────────
UPDATE_THRESHOLD = 0.82   # cosine similarity → update existing rule
SKIP_THRESHOLD   = 0.40   # below this → almost certainly not auditable

# ── Rules directories ─────────────────────────────────────────────────────────
_RULES_DIR  = Path(__file__).parent.parent.parent / "rules"
_DRAFT_DIR  = _RULES_DIR / "draft"

# ── Known database schema for the SQL generation prompt ──────────────────────
_DB_SCHEMA = """
## Database Schema

### hr_schema.employees
| Column      | Type        | Notes                                  |
|-------------|-------------|----------------------------------------|
| id          | UUID        | Primary key                            |
| full_name   | TEXT        | Employee full name                     |
| department  | TEXT        | Department name                        |
| hr_status   | TEXT        | 'Active', 'Terminated', 'On Leave'     |
| updated_at  | TIMESTAMPTZ | Last HR record update                  |
| created_at  | TIMESTAMPTZ | Date joined                            |

### app_security.network_logins
| Column          | Type        | Notes                                     |
|-----------------|-------------|-------------------------------------------|
| login_id        | UUID        | Primary key                               |
| employee_id     | UUID        | FK → hr_schema.employees.id               |
| login_timestamp | TIMESTAMPTZ | When the login attempt occurred           |
| status          | TEXT        | 'Success' or 'Failed'                     |
| ip_address      | INET        | Source IP address                         |

### app_security.application_permissions
| Column          | Type        | Notes                                     |
|-----------------|-------------|-------------------------------------------|
| perm_id         | INT         | Primary key                               |
| employee_id     | UUID        | FK → hr_schema.employees.id               |
| app_name        | TEXT        | Application name                          |
| permission_name | TEXT        | Permission / role name                    |
| is_privileged   | BOOLEAN     | True for admin/DBA/root roles             |
| last_used_at    | TIMESTAMPTZ | Last time permission was exercised        |

### app_security.cloud_credentials
| Column               | Type        | Notes                                 |
|----------------------|-------------|---------------------------------------|
| credential_id        | UUID        | Primary key                           |
| user_name            | TEXT        | IAM / cloud username                  |
| access_level         | TEXT        | 'Admin', 'Root', 'ReadOnly', etc.     |
| password_last_used   | TIMESTAMPTZ | Last password-based login             |
| access_key_last_used | TIMESTAMPTZ | Last API key usage                    |

### app_security.cloud_event_logs
| Column          | Type        | Notes                                     |
|-----------------|-------------|-------------------------------------------|
| event_id        | INT         | Primary key                               |
| log_source      | TEXT        | e.g. 'CloudTrail', 'AzureActivity'        |
| event_timestamp | TIMESTAMPTZ | When the event occurred                   |
| payload         | JSONB       | Raw event payload (AWS CloudTrail schema) |
"""

# ── Example YAML for few-shot prompting ──────────────────────────────────────
_EXAMPLE_YAML = """\
id: example_policy_check
title: "Example — Accounts Inactive for 30 Days"
severity: medium
threshold_days: 30
query: |
  SELECT
    e.id,
    e.full_name,
    e.department,
    e.hr_status,
    MAX(nl.login_timestamp) AS last_login_at
  FROM hr_schema.employees e
  LEFT JOIN app_security.network_logins nl
    ON nl.employee_id = e.id
    AND nl.status = 'Success'
  WHERE e.hr_status = 'Active'
  GROUP BY e.id, e.full_name, e.department, e.hr_status
  HAVING MAX(nl.login_timestamp) < NOW() - INTERVAL '{threshold_days} days'
     OR MAX(nl.login_timestamp) IS NULL
  ORDER BY last_login_at ASC NULLS FIRST
remediation: >
  Disable or suspend network accounts for active employees with no login
  activity beyond the threshold period. Escalate to the employee's manager
  and Information Security for review.
"""


# ---------------------------------------------------------------------------
# Gemini helpers
# ---------------------------------------------------------------------------

def _call_gemini(prompt: str, system: str = "") -> str | None:
    """Send a prompt to Gemini and return the text response."""
    if not settings.gemini_api_key:
        logger.error("GEMINI_API_KEY not set; cannot call Gemini.")
        return None

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
    )
    payload: dict[str, Any] = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1},
    }
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}

    try:
        resp = httpx.post(url, json=payload, timeout=90.0)
        resp.raise_for_status()
        result = resp.json()
        return result["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as exc:
        logger.error(f"Gemini call failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# Existing rule helpers
# ---------------------------------------------------------------------------

def _load_existing_rules() -> list[dict]:
    """Load all YAML rules from the main rules directory."""
    rules = []
    if not _RULES_DIR.exists():
        return rules
    for path in _RULES_DIR.glob("*.yaml"):
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if isinstance(data, dict) and "id" in data:
                    data["_file_path"] = str(path)
                    rules.append(data)
        except Exception as exc:
            logger.warning(f"Could not load rule {path}: {exc}")
    return rules


def _get_rule_summaries(rules: list[dict]) -> list[str]:
    """Build short text snippets for each rule (used for similarity search)."""
    summaries = []
    for rule in rules:
        summary = f"{rule.get('title', '')}. {rule.get('remediation', '')[:200]}"
        summaries.append(summary)
    return summaries


# ---------------------------------------------------------------------------
# Parameter extraction
# ---------------------------------------------------------------------------

_DAYS_RE    = re.compile(r"(\d+)\s*(?:calendar\s+)?days?", re.IGNORECASE)
_MINUTES_RE = re.compile(r"(\d+)\s*minutes?", re.IGNORECASE)
_ATTEMPTS_RE = re.compile(r"(\d+)\s*(?:consecutive\s+)?(?:failed\s+)?(?:login\s+)?attempts?", re.IGNORECASE)
_BYTES_RE   = re.compile(r"(\d+(?:\.\d+)?)\s*(GB|MB|KB|bytes?)", re.IGNORECASE)

_BYTES_MULTIPLIERS = {"GB": 1_073_741_824, "MB": 1_048_576, "KB": 1_024, "BYTES": 1, "BYTE": 1}

def _extract_parameters(text: str, rule: dict) -> list[ParameterChange]:
    """
    Heuristically extract numeric parameters from clause text and compare
    against the current rule's configured values.
    """
    changes: list[ParameterChange] = []

    if "threshold_days" in rule:
        m = _DAYS_RE.search(text)
        if m:
            new_val = int(m.group(1))
            old_val = rule["threshold_days"]
            if new_val != old_val:
                changes.append(ParameterChange(
                    field="threshold_days", old_value=old_val, new_value=new_val
                ))

    if "window_minutes" in rule:
        m = _MINUTES_RE.search(text)
        if m:
            new_val = int(m.group(1))
            old_val = rule["window_minutes"]
            if new_val != old_val:
                changes.append(ParameterChange(
                    field="window_minutes", old_value=old_val, new_value=new_val
                ))

    if "bytes_threshold" in rule:
        m = _BYTES_RE.search(text)
        if m:
            num = float(m.group(1))
            unit = m.group(2).upper().rstrip("S") + "S" if not m.group(2).upper().endswith("S") else m.group(2).upper()
            unit_key = m.group(2).upper()
            multiplier = _BYTES_MULTIPLIERS.get(unit_key, 1)
            new_val = int(num * multiplier)
            old_val = rule["bytes_threshold"]
            if new_val != old_val:
                changes.append(ParameterChange(
                    field="bytes_threshold", old_value=old_val, new_value=new_val
                ))

    return changes


def _apply_parameter_changes(rule: dict, changes: list[ParameterChange]) -> None:
    """Write updated parameter values back to the YAML file on disk."""
    if not changes or "_file_path" not in rule:
        return

    file_path = Path(rule["_file_path"])
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    for change in changes:
        old_line = f"{change.field}: {change.old_value}"
        new_line = f"{change.field}: {change.new_value}"
        content = content.replace(old_line, new_line)
        logger.info(
            f"Updated {file_path.name}: {change.field} "
            f"{change.old_value} → {change.new_value}"
        )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


# ---------------------------------------------------------------------------
# New rule generation
# ---------------------------------------------------------------------------

def _sanitize_yaml_id(text: str) -> str:
    """Convert arbitrary text to a safe snake_case rule ID."""
    s = re.sub(r"[^\w\s]", "", text.lower())
    s = re.sub(r"\s+", "_", s.strip())
    return s[:60]


def _generate_new_rule_yaml(clause: PolicyClause) -> str | None:
    """Ask Gemini to draft a complete YAML audit rule for this clause."""
    prompt = textwrap.dedent(f"""
        You are an expert compliance engineer designing automated database audit rules.

        Given the policy clause below, generate a complete YAML audit rule that matches
        the exact format of the example provided. The rule must:
        - Have a unique `id` in snake_case that describes the check
        - Have a `title` with a clear, descriptive name
        - Have `severity` set to one of: low, medium, high, critical
        - Include numeric threshold fields (threshold_days, window_minutes, bytes_threshold)
          ONLY if the clause specifies a measurable limit
        - Have a `query` in PostgreSQL that targets the schema below
        - Use template placeholders like {{threshold_days}} only for the fields you declared
        - Have a `remediation` with actionable steps for the compliance team
        - Output ONLY valid YAML — no markdown fences, no explanations

        {_DB_SCHEMA}

        ## Example YAML rule (match this format exactly):
        {_EXAMPLE_YAML}

        ## Policy Clause to audit:
        Section: {clause.section_path}
        Title: {clause.title}
        Text: {clause.full_text}

        ## Output (YAML only):
    """)

    system = (
        "You are a precise compliance engineer. "
        "Output only valid YAML with no code fences or extra text."
    )

    raw = _call_gemini(prompt, system)
    if not raw:
        return None

    # Strip any accidental code fences
    raw = re.sub(r"^```(?:yaml)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"^```\s*$", "", raw, flags=re.MULTILINE)
    raw = raw.strip()

    # Validate it parses as YAML and has required fields
    try:
        parsed = yaml.safe_load(raw)
        required = {"id", "title", "severity", "query", "remediation"}
        if not isinstance(parsed, dict) or not required.issubset(parsed.keys()):
            logger.warning("Generated YAML missing required fields; skipping.")
            return None
        return raw
    except yaml.YAMLError as exc:
        logger.warning(f"Generated YAML is invalid: {exc}")
        return None


def _is_auditable(clause: PolicyClause) -> tuple[bool, str]:
    """
    Ask Gemini whether the clause can be mechanically audited with a SQL query.
    Returns (is_auditable, reasoning).
    """
    prompt = textwrap.dedent(f"""
        Evaluate whether the following policy clause can be automatically audited
        by running a SQL query against a database that tracks employee logins,
        application permissions, and cloud credentials.

        Answer ONLY with a JSON object in this exact format:
        {{"auditable": true/false, "reason": "brief explanation"}}

        Policy clause:
        Title: {clause.title}
        Text: {clause.full_text}
    """)

    raw = _call_gemini(prompt)
    if not raw:
        return False, "Gemini unavailable"

    # Extract JSON even if surrounded by extra text
    json_match = re.search(r"\{.*?\}", raw, re.DOTALL)
    if not json_match:
        return False, "Could not parse Gemini response"

    try:
        result = json.loads(json_match.group())
        return bool(result.get("auditable", False)), result.get("reason", "")
    except json.JSONDecodeError:
        return False, "JSON parse error"


# ---------------------------------------------------------------------------
# Write draft rule to disk
# ---------------------------------------------------------------------------

def _write_draft_rule(yaml_content: str, clause: PolicyClause) -> str:
    """Write a generated YAML string to rules/draft/ and return the filename."""
    _DRAFT_DIR.mkdir(parents=True, exist_ok=True)

    # Derive filename from the rule's `id` field
    try:
        parsed = yaml.safe_load(yaml_content)
        rule_id = parsed.get("id") or _sanitize_yaml_id(clause.title)
    except Exception:
        rule_id = _sanitize_yaml_id(clause.title)

    filename = f"{rule_id}.yaml"
    path = _DRAFT_DIR / filename

    with open(path, "w", encoding="utf-8") as f:
        f.write(yaml_content)

    logger.info(f"Draft rule written: {path}")
    return filename


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def analyse_clause(clause: PolicyClause) -> RuleAction:
    """
    Determine the appropriate action for a single policy clause.

    Returns a RuleAction with action = "update" | "create" | "skip".
    """
    existing_rules = _load_existing_rules()
    rule_summaries  = _get_rule_summaries(existing_rules)

    # ── Embed the clause ──────────────────────────────────────────────────────
    clause_text = f"{clause.title}. {clause.full_text}"
    try:
        clause_vector = embed_texts([clause_text], task="retrieval.query")[0]
    except RuntimeError as exc:
        logger.warning(f"Embedding failed for clause '{clause.clause_id}': {exc}")
        return RuleAction(
            action="skip",
            clause=clause,
            confidence=0.0,
            reasoning=f"Embedding service unavailable: {exc}",
        )

    # ── Embed existing rule summaries and find the best match ─────────────────
    best_match_rule: dict | None = None
    best_score = 0.0

    if rule_summaries and existing_rules:
        try:
            rule_vectors = embed_texts(rule_summaries, task="retrieval.passage")
            # Cosine similarity (vectors are unit-length from Jina by default)
            for rule, rvec in zip(existing_rules, rule_vectors):
                dot = sum(a * b for a, b in zip(clause_vector, rvec))
                norm_c = sum(x * x for x in clause_vector) ** 0.5
                norm_r = sum(x * x for x in rvec) ** 0.5
                score = dot / (norm_c * norm_r + 1e-9)
                if score > best_score:
                    best_score = score
                    best_match_rule = rule
        except RuntimeError:
            logger.warning("Could not embed existing rules for comparison.")

    logger.info(
        f"Clause '{clause.clause_id}' best rule match: "
        f"'{best_match_rule.get('id') if best_match_rule else None}' "
        f"(score={best_score:.3f})"
    )

    # ── Decision: UPDATE ──────────────────────────────────────────────────────
    if best_score >= UPDATE_THRESHOLD and best_match_rule is not None:
        changes = _extract_parameters(clause.full_text, best_match_rule)
        if changes:
            _apply_parameter_changes(best_match_rule, changes)
            return RuleAction(
                action="update",
                clause=clause,
                matched_rule_id=best_match_rule.get("id"),
                parameter_changes=changes,
                confidence=best_score,
                reasoning=(
                    f"Clause matched rule '{best_match_rule.get('id')}' "
                    f"with similarity {best_score:.3f}. "
                    f"Updated {len(changes)} parameter(s)."
                ),
            )
        else:
            # High similarity but no extractable parameters — the rule is
            # already aligned with the policy; treat as skip.
            return RuleAction(
                action="skip",
                clause=clause,
                matched_rule_id=best_match_rule.get("id"),
                confidence=best_score,
                reasoning=(
                    f"Clause matched rule '{best_match_rule.get('id')}' "
                    f"(score={best_score:.3f}) but no parameter changes detected. "
                    "Rule is already aligned with this policy clause."
                ),
            )

    # ── Decision: possibly CREATE ─────────────────────────────────────────────
    auditable, reason = _is_auditable(clause)
    logger.info(f"Clause '{clause.clause_id}' auditable={auditable}: {reason}")

    if not auditable:
        return RuleAction(
            action="skip",
            clause=clause,
            confidence=best_score,
            reasoning=f"Clause is not mechanically auditable. Reason: {reason}",
        )

    # Try to generate a new YAML rule
    generated_yaml = _generate_new_rule_yaml(clause)
    if not generated_yaml:
        return RuleAction(
            action="skip",
            clause=clause,
            confidence=best_score,
            reasoning="Gemini returned an invalid or empty YAML draft.",
        )

    draft_filename = _write_draft_rule(generated_yaml, clause)
    return RuleAction(
        action="create",
        clause=clause,
        generated_yaml=generated_yaml,
        draft_filename=draft_filename,
        confidence=best_score,
        reasoning=f"New draft rule created: {draft_filename}. {reason}",
    )
