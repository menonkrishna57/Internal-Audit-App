"""
pdf_parser.py — Extracts text from a policy PDF and splits it into
structured PolicyClause objects using PyMuPDF (fitz).

Design decisions
----------------
* Assumes selectable (digital) text — no OCR.
* Clause detection is heading-driven: a line is treated as a heading
  when it matches the pattern ``<digits><dot><digits>…  <TITLE TEXT>``
  (e.g. "4.3  Account Management" or "7.4.1 Password Rotation").
* Falls back to paragraph-based chunking if no numbered headings are found
  (common for narrative-style policies without sections).
* Policy version is extracted from the first page if a line contains
  the pattern "version", "v\\d" or "rev" (case-insensitive).
"""
from __future__ import annotations

import re
import logging
import uuid
from datetime import datetime, timezone
from typing import IO

import fitz  # PyMuPDF

from app.policy_engine.models import PolicyClause

logger = logging.getLogger("audit_tool.policy_engine.pdf_parser")

# ── Regex helpers ───────────────────────────────────────────────────────────

# Matches numbered headings like "4.", "4.3", "4.3.1", "4.3.1.2"
_HEADING_RE = re.compile(r"^(\d+(?:\.\d+)*\.?)\s+(.+)$")

# Matches version strings in the first 200 characters of the first page
_VERSION_RE = re.compile(
    r"(?:version|rev(?:ision)?|v)\s*[:\-]?\s*(\d+(?:\.\d+)*)",
    re.IGNORECASE,
)

# Minimum characters for a clause to be considered non-trivial
_MIN_CLAUSE_LENGTH = 40


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_policy_pdf(
    file_bytes: bytes,
    source_filename: str,
) -> list[PolicyClause]:
    """
    Parse a PDF from raw bytes and return a list of PolicyClause objects.

    Parameters
    ----------
    file_bytes :
        Raw PDF content (e.g. from ``await upload_file.read()``).
    source_filename :
        Original filename used to populate ``PolicyClause.source_pdf``.

    Returns
    -------
    list[PolicyClause]
        Ordered list of extracted clauses. May be empty if the PDF has no
        extractable text.
    """
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        logger.error(f"Failed to open PDF '{source_filename}': {exc}")
        return []

    logger.info(f"Opened '{source_filename}' — {doc.page_count} page(s).")

    # ── Collect all text lines with their page numbers ──────────────────────
    all_lines: list[tuple[int, str]] = []  # (page_number_1indexed, line_text)
    first_page_text = ""

    for page_index in range(doc.page_count):
        page = doc.load_page(page_index)
        page_text = page.get_text("text")

        if page_index == 0:
            first_page_text = page_text[:400]

        for line in page_text.splitlines():
            stripped = line.strip()
            if stripped:
                all_lines.append((page_index + 1, stripped))

    doc.close()

    # ── Extract policy version from the first page ───────────────────────────
    policy_version = _extract_version(first_page_text)
    if policy_version:
        logger.info(f"Detected policy version: {policy_version}")

    # ── Choose chunking strategy ─────────────────────────────────────────────
    has_headings = _has_numbered_headings(all_lines)
    logger.info(
        f"Chunking strategy: {'heading-based' if has_headings else 'paragraph-based'}"
    )

    if has_headings:
        clauses = _chunk_by_headings(all_lines, source_filename, policy_version)
    else:
        clauses = _chunk_by_paragraphs(all_lines, source_filename, policy_version)

    logger.info(
        f"Extracted {len(clauses)} clause(s) from '{source_filename}'."
    )
    return clauses


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_version(text: str) -> str:
    """Return the first version string found in *text*, or empty string."""
    match = _VERSION_RE.search(text)
    return match.group(1) if match else ""


def _has_numbered_headings(lines: list[tuple[int, str]]) -> bool:
    """Return True when at least 2 numbered headings are found in the text."""
    count = sum(1 for _, line in lines if _HEADING_RE.match(line))
    return count >= 2


def _chunk_by_headings(
    lines: list[tuple[int, str]],
    source_pdf: str,
    policy_version: str,
) -> list[PolicyClause]:
    """
    Split text into clauses whenever a new numbered heading is encountered.

    The heading line becomes the ``title``. All subsequent lines until the
    next heading become the ``full_text`` of that clause.
    """
    clauses: list[PolicyClause] = []

    current_clause_id: str | None = None
    current_title: str = ""
    current_body_lines: list[str] = []
    current_page: int = 1
    section_stack: list[tuple[str, str]] = []  # (clause_id, title)

    def _flush():
        nonlocal current_clause_id, current_title, current_body_lines, current_page
        if current_clause_id is None:
            return
        body = " ".join(current_body_lines).strip()
        if len(body) >= _MIN_CLAUSE_LENGTH:
            # Build section path from the stack
            if section_stack:
                path_parts = [f"{cid} {t}" for cid, t in section_stack[-3:]]
                section_path = " > ".join(path_parts)
            else:
                section_path = current_title

            clauses.append(PolicyClause(
                clause_id=current_clause_id,
                title=current_title,
                full_text=body,
                page_number=current_page,
                section_path=section_path,
                source_pdf=source_pdf,
                policy_version=policy_version,
            ))
        current_clause_id = None
        current_title = ""
        current_body_lines = []

    for page_num, line in lines:
        m = _HEADING_RE.match(line)
        if m:
            _flush()  # save previous clause
            raw_id = m.group(1).rstrip(".")
            title_text = m.group(2).strip()
            current_clause_id = raw_id
            current_title = title_text
            current_page = page_num

            # Maintain a section stack for building breadcrumb paths
            depth = raw_id.count(".") + 1
            section_stack = section_stack[: depth - 1]
            section_stack.append((raw_id, title_text))
        else:
            if current_clause_id is not None:
                current_body_lines.append(line)

    _flush()  # flush the last clause
    return clauses


def _chunk_by_paragraphs(
    lines: list[tuple[int, str]],
    source_pdf: str,
    policy_version: str,
) -> list[PolicyClause]:
    """
    Fallback: split by blank-line-separated paragraphs.

    Each paragraph becomes one clause with a sequential ID.
    """
    clauses: list[PolicyClause] = []
    current_paragraph: list[str] = []
    current_page: int = 1
    clause_index = 1

    # Re-join adjacent non-blank lines into paragraphs.
    # Since we pre-stripped empty lines, we detect paragraph breaks by
    # looking for lines that are "short" (likely a title) followed by body.
    # We treat every 10 lines as a paragraph boundary as a last resort.

    PARA_MAX = 12  # max lines per paragraph chunk

    for page_num, line in lines:
        if not current_paragraph:
            current_page = page_num
        current_paragraph.append(line)

        if len(current_paragraph) >= PARA_MAX:
            text = " ".join(current_paragraph).strip()
            if len(text) >= _MIN_CLAUSE_LENGTH:
                clauses.append(PolicyClause(
                    clause_id=str(clause_index),
                    title=current_paragraph[0][:80],
                    full_text=text,
                    page_number=current_page,
                    section_path=f"Clause {clause_index}",
                    source_pdf=source_pdf,
                    policy_version=policy_version,
                ))
                clause_index += 1
            current_paragraph = []

    # Flush remaining lines
    if current_paragraph:
        text = " ".join(current_paragraph).strip()
        if len(text) >= _MIN_CLAUSE_LENGTH:
            clauses.append(PolicyClause(
                clause_id=str(clause_index),
                title=current_paragraph[0][:80],
                full_text=text,
                page_number=current_page,
                section_path=f"Clause {clause_index}",
                source_pdf=source_pdf,
                policy_version=policy_version,
            ))

    return clauses
