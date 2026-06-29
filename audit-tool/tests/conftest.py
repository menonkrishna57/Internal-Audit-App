import pytest
from pathlib import Path
from datetime import datetime, timezone
from app.engine import get_rules_dir, load_rules
from app.policy_engine.models import PolicyClause

@pytest.fixture(scope="session")
def rules_directory() -> Path:
    """Fixture returning the resolved path to the rules folder."""
    return get_rules_dir()

@pytest.fixture(scope="session")
def all_rules() -> list[dict]:
    """Fixture returning all loaded YAML rules from the rules folder."""
    return load_rules()

@pytest.fixture()
def sample_policy_clause() -> PolicyClause:
    """A reusable PolicyClause fixture for policy engine tests."""
    return PolicyClause(
        clause_id="4.3.1",
        title="Account Inactivity Policy",
        full_text=(
            "Employee accounts with no login activity for 30 calendar days "
            "shall be automatically suspended pending HR review."
        ),
        page_number=5,
        section_path="4. Access Control > 4.3 Account Management",
        source_pdf="it_security_policy_v2.pdf",
        policy_version="2.0",
        upload_timestamp=datetime(2026, 6, 23, 12, 0, 0, tzinfo=timezone.utc),
    )

@pytest.fixture()
def sample_policy_clauses(sample_policy_clause) -> list[PolicyClause]:
    """A list of PolicyClause objects for batch-operation tests."""
    return [
        sample_policy_clause,
        PolicyClause(
            clause_id="5.1.2",
            title="Failed Login Lockout",
            full_text=(
                "After 5 consecutive failed login attempts within a 10-minute window, "
                "the account shall be locked for 30 minutes."
            ),
            page_number=8,
            section_path="5. Authentication > 5.1 Login Controls",
            source_pdf="it_security_policy_v2.pdf",
            policy_version="2.0",
        ),
    ]
