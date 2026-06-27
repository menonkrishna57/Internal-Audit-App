"""
orchestrator.py — Top-level pipeline coordinator for PDF policy ingestion.

Usage
-----
    from app.policy_engine.orchestrator import process_policy_pdf

    result = await process_policy_pdf(file_bytes, filename)
    # result is a PolicyIngestionResult

Flow
----
1. Parse PDF  →  list[PolicyClause]
2. Attach source_pdf / policy_version to each clause
3. Upsert all clauses into Qdrant (embeddings + metadata)
4. For each clause: call rule_generator.analyse_clause()
5. Collect results and return PolicyIngestionResult
"""
from __future__ import annotations

import logging

from app.policy_engine.models import PolicyClause, PolicyIngestionResult, RuleAction
from app.policy_engine.pdf_parser import parse_policy_pdf
from app.policy_engine.rule_generator import analyse_clause
from app.policy_engine.vector_store import upsert_clauses

logger = logging.getLogger("audit_tool.policy_engine.orchestrator")


async def process_policy_pdf(
    file_bytes: bytes,
    source_filename: str,
) -> PolicyIngestionResult:
    """
    Full ingestion pipeline: parse → embed → store → analyse → return result.

    Parameters
    ----------
    file_bytes :
        Raw bytes of the uploaded PDF.
    source_filename :
        Original filename (used for traceability in Qdrant payloads).

    Returns
    -------
    PolicyIngestionResult
        Structured summary of every action taken (updates, creations, skips).
    """
    logger.info(f"Starting policy ingestion for '{source_filename}'...")

    # ── Step 1: Parse PDF into clauses ──────────────────────────────────────
    clauses: list[PolicyClause] = parse_policy_pdf(file_bytes, source_filename)

    if not clauses:
        logger.warning(f"No clauses extracted from '{source_filename}'.")
        return PolicyIngestionResult(
            source_pdf=source_filename,
            policy_version="",
            total_clauses=0,
            auditable_clauses=0,
            rules_updated=[],
            rules_created=[],
            clauses_skipped=[],
        )

    # Grab policy version from the first clause (all clauses share the same version)
    policy_version = clauses[0].policy_version
    logger.info(
        f"Parsed {len(clauses)} clause(s) from '{source_filename}' "
        f"(version: '{policy_version or 'unknown'}')."
    )

    # ── Step 2: Embed and store all clauses in Qdrant ───────────────────────
    try:
        upserted = upsert_clauses(clauses)
        logger.info(f"Upserted {upserted} clause(s) into Qdrant.")
    except RuntimeError as exc:
        # Jina key missing or Qdrant down — log but continue with rule analysis
        # (rule matching will fall back to skipping all clauses)
        logger.warning(
            f"Qdrant upsert failed (will skip semantic search): {exc}"
        )

    # ── Step 3: Analyse each clause ─────────────────────────────────────────
    actions: list[RuleAction] = []
    for clause in clauses:
        logger.debug(f"Analysing clause {clause.clause_id}: {clause.title}")
        action = analyse_clause(clause)
        actions.append(action)
        logger.info(
            f"  [{action.action.upper()}] clause '{clause.clause_id}' — "
            f"{action.reasoning[:120]}"
        )

    # ── Step 4: Partition results ────────────────────────────────────────────
    updated  = [a for a in actions if a.action == "update"]
    created  = [a for a in actions if a.action == "create"]
    skipped  = [a for a in actions if a.action == "skip"]

    result = PolicyIngestionResult(
        source_pdf=source_filename,
        policy_version=policy_version,
        total_clauses=len(clauses),
        auditable_clauses=len(updated) + len(created),
        rules_updated=updated,
        rules_created=created,
        clauses_skipped=skipped,
    )

    logger.info(
        f"Ingestion complete for '{source_filename}': "
        f"{len(updated)} rule(s) updated, "
        f"{len(created)} draft rule(s) created, "
        f"{len(skipped)} clause(s) skipped."
    )
    return result
