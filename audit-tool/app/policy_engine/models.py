"""
Shared Pydantic models and dataclasses for the policy engine pipeline.

These models are used across pdf_parser, vector_store, rule_generator,
and orchestrator to ensure consistent data shapes throughout.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# PDF Parsing
# ---------------------------------------------------------------------------

class PolicyClause(BaseModel):
    """
    A single extracted clause from a policy PDF document.

    Attributes
    ----------
    clause_id :
        Structured ID of the clause, e.g. "4.3.1". Falls back to a
        sequential index string if the PDF has no numbering.
    title :
        Short heading for this clause, e.g. "Account Inactivity Policy".
    full_text :
        Raw text of the clause as extracted from the PDF.
    page_number :
        1-indexed page number where this clause begins in the source PDF.
    section_path :
        Breadcrumb path, e.g. "4. Access Control > 4.3 Account Management".
    source_pdf :
        Original filename of the uploaded PDF (set by the orchestrator).
    policy_version :
        Optional version tag extracted from the document header / metadata,
        e.g. "v2.1". Populated by the parser when found.
    upload_timestamp :
        UTC timestamp at which this clause was ingested.
    """
    clause_id: str
    title: str
    full_text: str
    page_number: int
    section_path: str
    source_pdf: str = ""
    policy_version: str = ""
    upload_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Rule Generation
# ---------------------------------------------------------------------------

class ParameterChange(BaseModel):
    """A single numeric / string parameter to update in an existing YAML rule."""
    field: str          # e.g. "threshold_days"
    old_value: object   # original value in the YAML
    new_value: object   # extracted from the policy clause


class RuleAction(BaseModel):
    """
    Describes what the rule_generator decided to do for a given policy clause.

    Actions
    -------
    update  — modify parameter(s) in an existing YAML rule file.
    create  — write a brand-new draft YAML rule to rules/draft/.
    skip    — clause is informational / not directly auditable.
    """
    action: Literal["update", "create", "skip"]
    clause: PolicyClause
    matched_rule_id: str | None = None          # populated for "update" actions
    parameter_changes: list[ParameterChange] | None = None  # for "update"
    generated_yaml: str | None = None           # for "create"
    draft_filename: str | None = None           # e.g. "service_account_rotation.yaml"
    confidence: float = 0.0                     # 0.0 – 1.0
    reasoning: str = ""


# ---------------------------------------------------------------------------
# Orchestrator result
# ---------------------------------------------------------------------------

class PolicyIngestionResult(BaseModel):
    """
    Top-level result returned by the orchestrator after processing a PDF.
    This is what the API endpoint sends back to the caller.
    """
    ingestion_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_pdf: str
    policy_version: str = ""
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_clauses: int
    auditable_clauses: int
    rules_updated: list[RuleAction]
    rules_created: list[RuleAction]
    clauses_skipped: list[RuleAction]

    @property
    def summary(self) -> dict:
        return {
            "ingestion_id": self.ingestion_id,
            "source_pdf": self.source_pdf,
            "policy_version": self.policy_version,
            "ingested_at": self.ingested_at.isoformat(),
            "total_clauses": self.total_clauses,
            "rules_updated": len(self.rules_updated),
            "rules_created": len(self.rules_created),
            "clauses_skipped": len(self.clauses_skipped),
        }
