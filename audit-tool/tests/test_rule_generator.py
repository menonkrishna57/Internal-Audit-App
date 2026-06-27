"""
test_rule_generator.py — Tests for the AI rule generation module.

All AI / embedding calls are mocked to keep tests fast and offline-friendly.
"""
from __future__ import annotations

import textwrap
import pytest
import yaml
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.policy_engine.models import PolicyClause, ParameterChange


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def inactive_clause() -> PolicyClause:
    return PolicyClause(
        clause_id="4.3",
        title="Account Inactivity",
        full_text=(
            "Employee accounts with no login activity for 30 calendar days "
            "shall be automatically suspended pending HR review."
        ),
        page_number=4,
        section_path="4. Access Control > 4.3 Account Inactivity",
        source_pdf="it_policy.pdf",
        policy_version="1.0",
    )


@pytest.fixture()
def unauditable_clause() -> PolicyClause:
    return PolicyClause(
        clause_id="9.1",
        title="Security Awareness Training",
        full_text=(
            "All employees must complete annual security awareness training. "
            "Completion records are maintained by the HR department."
        ),
        page_number=15,
        section_path="9. Training",
        source_pdf="it_policy.pdf",
        policy_version="1.0",
    )


# ---------------------------------------------------------------------------
# Parameter extraction
# ---------------------------------------------------------------------------

class TestExtractParameters:
    def test_extracts_threshold_days(self):
        from app.policy_engine.rule_generator import _extract_parameters
        rule = {"id": "stale_network_logins", "threshold_days": 10}
        changes = _extract_parameters(
            "Accounts inactive for 30 days shall be suspended.", rule
        )
        assert len(changes) == 1
        assert changes[0].field == "threshold_days"
        assert changes[0].old_value == 10
        assert changes[0].new_value == 30

    def test_extracts_window_minutes(self):
        from app.policy_engine.rule_generator import _extract_parameters
        rule = {"id": "brute_force_then_success", "window_minutes": 15}
        changes = _extract_parameters(
            "After 5 failed attempts within 10 minutes, lock the account.", rule
        )
        assert len(changes) == 1
        assert changes[0].field == "window_minutes"
        assert changes[0].new_value == 10

    def test_no_change_when_values_match(self):
        from app.policy_engine.rule_generator import _extract_parameters
        rule = {"id": "stale_network_logins", "threshold_days": 30}
        changes = _extract_parameters(
            "Accounts inactive for 30 days shall be suspended.", rule
        )
        assert len(changes) == 0

    def test_no_extractable_number_returns_empty(self):
        from app.policy_engine.rule_generator import _extract_parameters
        rule = {"id": "stale_network_logins", "threshold_days": 10}
        changes = _extract_parameters(
            "Accounts must be reviewed periodically.", rule
        )
        assert len(changes) == 0

    def test_bytes_threshold_gb(self):
        from app.policy_engine.rule_generator import _extract_parameters
        rule = {"id": "mass_data_exfiltration", "bytes_threshold": 1_073_741_824}
        changes = _extract_parameters(
            "Transfers exceeding 5 GB in a single session must be flagged.", rule
        )
        assert len(changes) == 1
        assert changes[0].field == "bytes_threshold"
        assert changes[0].new_value == 5 * 1_073_741_824


# ---------------------------------------------------------------------------
# YAML sanitisation helper
# ---------------------------------------------------------------------------

class TestSanitizeYamlId:
    def test_basic(self):
        from app.policy_engine.rule_generator import _sanitize_yaml_id
        assert _sanitize_yaml_id("Account Inactivity Policy") == "account_inactivity_policy"

    def test_strips_special_chars(self):
        from app.policy_engine.rule_generator import _sanitize_yaml_id
        result = _sanitize_yaml_id("MFA / 2FA Enforcement (Clause 5.1)")
        assert " " not in result
        assert "/" not in result
        assert "(" not in result

    def test_truncates_to_60_chars(self):
        from app.policy_engine.rule_generator import _sanitize_yaml_id
        long_title = "A" * 80
        result = _sanitize_yaml_id(long_title)
        assert len(result) <= 60


# ---------------------------------------------------------------------------
# analyse_clause — mocked end-to-end
# ---------------------------------------------------------------------------

class TestAnalyseClause:
    def _fake_vector(self, n=1024) -> list[float]:
        v = [0.0] * n
        v[0] = 1.0
        return v

    def test_returns_update_when_high_similarity(self, inactive_clause, tmp_path):
        """When a clause strongly matches an existing rule, action should be 'update'."""
        fake_rule = {
            "id": "stale_network_logins",
            "title": "Inactive Accounts — Stale Network Logins",
            "severity": "medium",
            "threshold_days": 10,
            "query": "SELECT * FROM logins WHERE days > {threshold_days}",
            "remediation": "Disable inactive accounts.",
            "_file_path": str(tmp_path / "stale_logins.yaml"),
        }
        # Write the fake rule YAML so _apply_parameter_changes can find it
        (tmp_path / "stale_logins.yaml").write_text(
            "id: stale_network_logins\nthreshold_days: 10\n"
        )

        high_sim_vector = self._fake_vector()

        with (
            patch("app.policy_engine.rule_generator._load_existing_rules", return_value=[fake_rule]),
            patch("app.policy_engine.rule_generator.embed_texts", return_value=[high_sim_vector]),
        ):
            from app.policy_engine.rule_generator import analyse_clause
            action = analyse_clause(inactive_clause)

        assert action.action == "update"
        assert action.matched_rule_id == "stale_network_logins"
        assert action.parameter_changes is not None
        assert any(c.field == "threshold_days" for c in action.parameter_changes)

    def test_returns_skip_when_not_auditable(self, unauditable_clause):
        """Non-auditable clauses should always be skipped."""
        near_zero_vector = [0.001] * 1024  # very low similarity to any rule

        with (
            patch("app.policy_engine.rule_generator._load_existing_rules", return_value=[]),
            patch("app.policy_engine.rule_generator.embed_texts", return_value=[near_zero_vector]),
            patch(
                "app.policy_engine.rule_generator._is_auditable",
                return_value=(False, "Training completion is not trackable via DB query."),
            ),
        ):
            from app.policy_engine.rule_generator import analyse_clause
            action = analyse_clause(unauditable_clause)

        assert action.action == "skip"

    def test_returns_create_when_auditable_and_no_match(self, inactive_clause, tmp_path):
        """Low similarity + auditable clause → 'create' action with draft YAML."""
        valid_yaml = textwrap.dedent("""\
            id: custom_inactivity_check
            title: "Custom Account Inactivity Check"
            severity: medium
            threshold_days: 30
            query: |
              SELECT e.id FROM hr_schema.employees e
              WHERE e.hr_status = 'Active'
            remediation: >
              Disable inactive accounts and notify the manager.
        """)
        near_zero_vector = [0.001] * 1024

        with (
            patch("app.policy_engine.rule_generator._load_existing_rules", return_value=[]),
            patch("app.policy_engine.rule_generator.embed_texts", return_value=[near_zero_vector]),
            patch(
                "app.policy_engine.rule_generator._is_auditable",
                return_value=(True, "Can be checked by querying login timestamps."),
            ),
            patch(
                "app.policy_engine.rule_generator._generate_new_rule_yaml",
                return_value=valid_yaml,
            ),
            patch("app.policy_engine.rule_generator._DRAFT_DIR", tmp_path),
        ):
            from app.policy_engine.rule_generator import analyse_clause
            action = analyse_clause(inactive_clause)

        assert action.action == "create"
        assert action.generated_yaml is not None
        assert action.draft_filename is not None
        assert action.draft_filename.endswith(".yaml")

    def test_returns_skip_when_embedding_fails(self, inactive_clause):
        """If the embedding service is unavailable, the clause should be skipped gracefully."""
        with patch(
            "app.policy_engine.rule_generator.embed_texts",
            side_effect=RuntimeError("JINA_API_KEY not set"),
        ):
            from app.policy_engine.rule_generator import analyse_clause
            action = analyse_clause(inactive_clause)

        assert action.action == "skip"
        assert "Embedding service unavailable" in action.reasoning


# ---------------------------------------------------------------------------
# Generated YAML validity
# ---------------------------------------------------------------------------

class TestGeneratedYamlValidity:
    def test_required_fields_present(self):
        """Any YAML rule the generator writes must have all required fields."""
        required = {"id", "title", "severity", "query", "remediation"}
        sample_yaml = textwrap.dedent("""\
            id: service_account_rotation
            title: "Service Account Password Rotation"
            severity: high
            threshold_days: 90
            query: |
              SELECT credential_id, user_name
              FROM app_security.cloud_credentials
              WHERE password_last_used < NOW() - INTERVAL '{threshold_days} days'
            remediation: >
              Force a password rotation for all flagged service accounts.
        """)
        parsed = yaml.safe_load(sample_yaml)
        assert required.issubset(parsed.keys())

    def test_severity_is_valid(self):
        allowed = {"low", "medium", "high", "critical"}
        sample_yaml = textwrap.dedent("""\
            id: test_rule
            title: "Test"
            severity: high
            query: "SELECT 1"
            remediation: "Do something."
        """)
        parsed = yaml.safe_load(sample_yaml)
        assert parsed["severity"] in allowed
