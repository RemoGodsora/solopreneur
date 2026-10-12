import pytest
from core.validator import ContractValidator
from core.healer import SelfHealingEngine
from core.models import ViolationType

CONTRACT_PATH = "contracts/orders_v1.yaml"
CLEAN_DATA_PATH = "data/orders_clean.csv"
CORRUPTED_DATA_PATH = "data/orders_corrupted.csv"

def test_clean_data_passes_contract():
    validator = ContractValidator(CONTRACT_PATH)
    result = validator.validate_file(CLEAN_DATA_PATH)
    
    assert result.is_valid is True
    assert len(result.violations) == 0
    assert result.total_rows_inspected == 500

def test_corrupted_data_catches_all_drift_types():
    validator = ContractValidator(CONTRACT_PATH)
    result = validator.validate_file(CORRUPTED_DATA_PATH)
    
    assert result.is_valid is False
    assert len(result.violations) > 0

    violation_types = {v.violation_type for v in result.violations}
    
    # Assert structural drift detection
    assert ViolationType.MISSING_COLUMN in violation_types
    assert ViolationType.EXTRA_COLUMN in violation_types
    
    # Assert data-level constraints detection
    assert ViolationType.NULL_VIOLATION in violation_types
    assert ViolationType.ENUM_VIOLATION in violation_types
    assert ViolationType.RANGE_VIOLATION in violation_types
    assert ViolationType.QUALITY_RULE_FAILED in violation_types

def test_self_healing_view_produces_valid_output():
    validator = ContractValidator(CONTRACT_PATH)
    result = validator.validate_file(CORRUPTED_DATA_PATH)
    
    healer = SelfHealingEngine(validator.contract)
    view_sql = healer.generate_healing_view(CORRUPTED_DATA_PATH, result)
    
    # Execute the generated view in DuckDB
    validator.conn.execute(view_sql)
    healed_count = validator.conn.execute(
        f"SELECT COUNT(*) FROM v_{validator.contract.dataset}_healed;"
    ).fetchone()[0]
    
    # Must yield valid sanitized rows
    assert healed_count > 400

    # Ensure no NULLs exist in healed mandatory columns
    null_cust_count = validator.conn.execute(
        f"SELECT COUNT(*) FROM v_{validator.contract.dataset}_healed WHERE customer_id IS NULL OR customer_id = '';"
    ).fetchone()[0]
    assert null_cust_count == 0