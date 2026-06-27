"""
test_pdf_parser.py — Unit tests for the PDF parsing module.

Tests are designed to work without requiring an actual PDF on disk by
constructing minimal in-memory PDFs using PyMuPDF (fitz).
"""
from __future__ import annotations

import io
import pytest
import fitz  # PyMuPDF

from app.policy_engine.pdf_parser import (
    _extract_version,
    _has_numbered_headings,
    _chunk_by_headings,
    _chunk_by_paragraphs,
    parse_policy_pdf,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pdf_bytes(text: str) -> bytes:
    """Create a minimal single-page PDF containing *text*."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text, fontsize=11)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Version extraction
# ---------------------------------------------------------------------------

class TestExtractVersion:
    def test_version_with_keyword(self):
        assert _extract_version("IT Security Policy Version 2.1") == "2.1"

    def test_version_lowercase_v(self):
        assert _extract_version("Policy v3.0 approved by CISO") == "3.0"

    def test_revision_keyword(self):
        assert _extract_version("Revision: 1.4") == "1.4"

    def test_no_version_returns_empty(self):
        assert _extract_version("This document has no version information.") == ""

    def test_first_version_wins(self):
        # Should return the first match, not the second
        result = _extract_version("Version 1.0 supersedes version 2.0")
        assert result == "1.0"


# ---------------------------------------------------------------------------
# Heading detection
# ---------------------------------------------------------------------------

class TestHasNumberedHeadings:
    def test_detects_numbered_headings(self):
        lines = [
            (1, "1 Introduction"),
            (1, "Some introductory text here about the policy."),
            (2, "2 Scope"),
            (2, "This policy applies to all employees."),
        ]
        assert _has_numbered_headings(lines) is True

    def test_no_headings_returns_false(self):
        lines = [
            (1, "All employees must comply with this policy."),
            (1, "Failure to comply may result in disciplinary action."),
        ]
        assert _has_numbered_headings(lines) is False

    def test_single_heading_insufficient(self):
        lines = [
            (1, "1 Introduction"),
            (1, "Some text."),
        ]
        assert _has_numbered_headings(lines) is False


# ---------------------------------------------------------------------------
# Heading-based chunking
# ---------------------------------------------------------------------------

class TestChunkByHeadings:
    def _make_lines(self):
        return [
            (1, "1 Introduction"),
            (1, "This document sets out the policies for all employees."),
            (1, "All staff must adhere to these requirements."),
            (2, "2 Access Control"),
            (2, "Employee accounts inactive for 30 days shall be suspended."),
            (2, "Access must be reviewed quarterly by the CISO."),
            (3, "2.1 Password Management"),
            (3, "Passwords must be rotated every 90 days."),
            (3, "Minimum password length is 12 characters."),
        ]

    def test_correct_number_of_clauses(self):
        clauses = _chunk_by_headings(self._make_lines(), "policy.pdf", "1.0")
        assert len(clauses) == 3

    def test_clause_ids_are_correct(self):
        clauses = _chunk_by_headings(self._make_lines(), "policy.pdf", "1.0")
        ids = [c.clause_id for c in clauses]
        assert ids == ["1", "2", "2.1"]

    def test_source_pdf_is_set(self):
        clauses = _chunk_by_headings(self._make_lines(), "test.pdf", "2.0")
        for clause in clauses:
            assert clause.source_pdf == "test.pdf"

    def test_policy_version_is_set(self):
        clauses = _chunk_by_headings(self._make_lines(), "test.pdf", "2.0")
        for clause in clauses:
            assert clause.policy_version == "2.0"

    def test_section_path_populated(self):
        clauses = _chunk_by_headings(self._make_lines(), "test.pdf", "")
        # The last clause (2.1) should reference parent sections
        sub = next(c for c in clauses if c.clause_id == "2.1")
        assert "2" in sub.section_path  # parent section id should appear


# ---------------------------------------------------------------------------
# Paragraph-based chunking (fallback)
# ---------------------------------------------------------------------------

class TestChunkByParagraphs:
    def _make_lines(self, line_count: int = 30):
        return [(1, f"Policy line number {i + 1} with some meaningful content.") for i in range(line_count)]

    def test_produces_clauses(self):
        clauses = _chunk_by_paragraphs(self._make_lines(), "policy.pdf", "")
        assert len(clauses) > 0

    def test_clause_ids_are_sequential(self):
        clauses = _chunk_by_paragraphs(self._make_lines(), "policy.pdf", "")
        ids = [int(c.clause_id) for c in clauses]
        assert ids == list(range(1, len(ids) + 1))


# ---------------------------------------------------------------------------
# End-to-end parse_policy_pdf
# ---------------------------------------------------------------------------

class TestParsePolicyPdf:
    def test_empty_bytes_returns_empty_list(self):
        result = parse_policy_pdf(b"", "empty.pdf")
        assert result == []

    def test_invalid_bytes_returns_empty_list(self):
        result = parse_policy_pdf(b"not a pdf at all", "fake.pdf")
        assert result == []

    def test_real_pdf_returns_clauses(self):
        text = (
            "IT Security Policy  Version 1.2\n\n"
            "1 Introduction\n"
            "This policy governs all aspects of information security.\n"
            "All employees are required to comply with these guidelines.\n\n"
            "2 Account Management\n"
            "Accounts inactive for 30 days shall be suspended automatically.\n"
            "The HR team must notify Information Security within 24 hours.\n"
        )
        pdf_bytes = _make_pdf_bytes(text)
        clauses = parse_policy_pdf(pdf_bytes, "it_security_policy.pdf")
        assert len(clauses) > 0
        for clause in clauses:
            assert clause.source_pdf == "it_security_policy.pdf"
            assert len(clause.full_text) > 0
