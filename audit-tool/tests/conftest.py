import pytest
from pathlib import Path
from app.engine import get_rules_dir, load_rules

@pytest.fixture(scope="session")
def rules_directory() -> Path:
    """Fixture returning the resolved path to the rules folder."""
    return get_rules_dir()

@pytest.fixture(scope="session")
def all_rules() -> list[dict]:
    """Fixture returning all loaded YAML rules from the rules folder."""
    return load_rules()
