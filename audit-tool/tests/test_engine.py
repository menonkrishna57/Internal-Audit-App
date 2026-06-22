import pytest
import sqlparse
from app.engine import build_sql_query

def test_yaml_rules_loaded(all_rules):
    """Ensure that the rules are successfully loaded and we have exactly 8 rules."""
    assert len(all_rules) == 8, f"Expected exactly 8 rules, found {len(all_rules)}"

def test_rule_schemas(all_rules):
    """Ensure all required fields are present in the YAML schema."""
    required_keys = {"id", "title", "severity", "query", "remediation"}
    for rule in all_rules:
        rule_id = rule.get("id")
        for key in required_keys:
            assert key in rule, f"Rule '{rule_id}' is missing required key '{key}'"

def test_unique_rule_ids(all_rules):
    """Ensure all rules have unique IDs."""
    rule_ids = [rule.get("id") for rule in all_rules]
    assert len(rule_ids) == len(set(rule_ids)), f"Duplicate rule IDs found: {rule_ids}"

def test_rule_severities(all_rules):
    """Ensure severity matches allowed values: low, medium, high, critical."""
    allowed_severities = {"low", "medium", "high", "critical"}
    for rule in all_rules:
        severity = rule.get("severity")
        rule_id = rule.get("id")
        assert severity in allowed_severities, f"Rule '{rule_id}' has invalid severity '{severity}'"

def test_rule_query_sql_syntax(all_rules):
    """Ensure the queries parse successfully as SQL via sqlparse and are not empty."""
    for rule in all_rules:
        rule_id = rule.get("id")
        sql = build_sql_query(rule)
        
        assert sql.strip() != "", f"Rule '{rule_id}' generated an empty query string"
        
        # Parse SQL syntax
        parsed = sqlparse.parse(sql)
        assert len(parsed) > 0, f"Rule '{rule_id}' has invalid SQL syntax"
        
        # Verify it has statement tokens
        for statement in parsed:
            assert len(statement.tokens) > 0, f"Rule '{rule_id}' parsed statement has no tokens"

def test_configurable_fields_injection():
    """Ensure that config thresholds (threshold_days, window_minutes, bytes_threshold) are correctly formatted into SQL queries."""
    
    # 1. Test stale logins rule formats threshold_days
    stale_logins_rule = {
        "id": "stale_network_logins",
        "threshold_days": 30,
        "query": "SELECT * FROM logins WHERE days > {threshold_days}"
    }
    sql = build_sql_query(stale_logins_rule)
    assert "days > 30" in sql

    # 2. Test impossible travel formats window_minutes
    impossible_travel_rule = {
        "id": "impossible_travel_logins",
        "window_minutes": 60,
        "query": "SELECT * FROM logins WHERE diff < {window_minutes}"
    }
    sql = build_sql_query(impossible_travel_rule)
    assert "diff < 60" in sql

    # 3. Test mass data exfiltration formats bytes_threshold
    exfiltration_rule = {
        "id": "mass_data_exfiltration",
        "bytes_threshold": 5000,
        "query": "SELECT * FROM logs WHERE bytes > {bytes_threshold}"
    }
    sql = build_sql_query(exfiltration_rule)
    assert "bytes > 5000" in sql

def test_sod_conflict_pairs_generation():
    """Ensure the segregation of duties rule formats a UNION query based on conflict pairs."""
    sod_rule = {
        "id": "segregation_of_duties",
        "conflict_pairs": [
            {"app": "AppA", "roles": ["RoleA1", "RoleA2"]},
            {"app": "AppB", "roles": ["RoleB1", "RoleB2"]}
        ],
        "query": "placeholder"
    }
    
    sql = build_sql_query(sod_rule)
    
    # Verify both app names are present in the generated union query
    assert "AppA" in sql
    assert "RoleA1" in sql
    assert "RoleA2" in sql
    
    assert "AppB" in sql
    assert "RoleB1" in sql
    assert "RoleB2" in sql
    
    # Should contain UNION since there are multiple pairs
    assert "UNION" in sql
