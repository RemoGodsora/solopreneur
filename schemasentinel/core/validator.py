import os
import yaml
import duckdb
from typing import List
from core.models import DataContract, ValidationResult, Violation, ViolationType

class ContractValidator:
    def __init__(self, contract_path: str):
        if not os.path.exists(contract_path):
            raise FileNotFoundError(f"Contract file not found at: {contract_path}")
        
        with open(contract_path, "r", encoding="utf-8") as f:
            raw_yaml = yaml.safe_load(f)
        
        self.contract = DataContract(**raw_yaml)
        self.conn = duckdb.connect(database=":memory:")

    def validate_file(self, data_file_path: str) -> ValidationResult:
        if not os.path.exists(data_file_path):
            raise FileNotFoundError(f"Data file not found: {data_file_path}")

        # Register data view into DuckDB based on file format
        ext = os.path.splitext(data_file_path)[1].lower()
        if ext == ".parquet":
            read_func = f"read_parquet('{data_file_path}')"
        elif ext == ".csv":
            read_func = f"read_csv_auto('{data_file_path}')"
        elif ext in [".json", ".jsonl"]:
            read_func = f"read_json_auto('{data_file_path}')"
        else:
            raise ValueError(f"Unsupported file extension: {ext}")

        self.conn.execute(f"CREATE OR REPLACE VIEW target_data AS SELECT * FROM {read_func};")
        
        total_rows = self.conn.execute("SELECT COUNT(*) FROM target_data;").fetchone()[0]
        violations: List[Violation] = []

        # 1. Structural Validation (Column Names and Types)
        observed_cols_meta = self.conn.execute("DESCRIBE target_data;").fetchall()
        observed_cols = {col[0]: col[1].upper() for col in observed_cols_meta}

        expected_col_map = {col.name: col for col in self.contract.schema_def.columns}

        # Check for missing columns
        for exp_col_name in expected_col_map:
            if exp_col_name not in observed_cols:
                violations.append(Violation(
                    column=exp_col_name,
                    violation_type=ViolationType.MISSING_COLUMN,
                    details=f"Required column '{exp_col_name}' is missing from incoming dataset.",
                    failed_rows_count=total_rows
                ))

        # Check for extra unexpected columns
        for obs_col in observed_cols:
            if obs_col not in expected_col_map:
                violations.append(Violation(
                    column=obs_col,
                    violation_type=ViolationType.EXTRA_COLUMN,
                    details=f"Undocumented column '{obs_col}' detected in dataset.",
                    failed_rows_count=0
                ))

        # Check data type mappings
        for col_name, col_contract in expected_col_map.items():
            if col_name in observed_cols:
                obs_type = observed_cols[col_name]
                exp_type = col_contract.type.upper()
                if obs_type != exp_type and not self._is_compatible_type(obs_type, exp_type):
                    violations.append(Violation(
                        column=col_name,
                        violation_type=ViolationType.TYPE_MISMATCH,
                        details=f"Column '{col_name}' type mismatch: expected {exp_type}, observed {obs_type}.",
                        failed_rows_count=total_rows
                    ))

        # 2. Field-Level Constraints
        for col_contract in self.contract.schema_def.columns:
            col = col_contract.name
            if col not in observed_cols:
                continue

            # Nullability check
            if not col_contract.nullable:
                null_count = self.conn.execute(
                    f"SELECT COUNT(*) FROM target_data WHERE {col} IS NULL;"
                ).fetchone()[0]
                if null_count > 0:
                    violations.append(Violation(
                        column=col,
                        violation_type=ViolationType.NULL_VIOLATION,
                        details=f"Non-nullable column '{col}' contains {null_count} NULL entries.",
                        failed_rows_count=null_count
                    ))

            # Uniqueness check
            if col_contract.unique:
                dup_count = self.conn.execute(
                    f"SELECT COUNT(*) - COUNT(DISTINCT {col}) FROM target_data WHERE {col} IS NOT NULL;"
                ).fetchone()[0]
                if dup_count > 0:
                    violations.append(Violation(
                        column=col,
                        violation_type=ViolationType.UNIQUENESS_VIOLATION,
                        details=f"Unique column '{col}' has {dup_count} duplicate values.",
                        failed_rows_count=dup_count
                    ))

            # Range checks
            if col_contract.min_value is not None:
                under_count = self.conn.execute(
                    f"SELECT COUNT(*) FROM target_data WHERE {col} < {col_contract.min_value};"
                ).fetchone()[0]
                if under_count > 0:
                    violations.append(Violation(
                        column=col,
                        violation_type=ViolationType.RANGE_VIOLATION,
                        details=f"Column '{col}' has {under_count} values below min threshold {col_contract.min_value}.",
                        failed_rows_count=under_count
                    ))

            if col_contract.max_value is not None:
                over_count = self.conn.execute(
                    f"SELECT COUNT(*) FROM target_data WHERE {col} > {col_contract.max_value};"
                ).fetchone()[0]
                if over_count > 0:
                    violations.append(Violation(
                        column=col,
                        violation_type=ViolationType.RANGE_VIOLATION,
                        details=f"Column '{col}' has {over_count} values above max threshold {col_contract.max_value}.",
                        failed_rows_count=over_count
                    ))

            # Allowed values (Enum check)
            if col_contract.allowed_values:
                allowed_formatted = ", ".join([f"'{v}'" for v in col_contract.allowed_values])
                enum_count = self.conn.execute(
                    f"SELECT COUNT(*) FROM target_data WHERE {col} NOT IN ({allowed_formatted}) AND {col} IS NOT NULL;"
                ).fetchone()[0]
                if enum_count > 0:
                    violations.append(Violation(
                        column=col,
                        violation_type=ViolationType.ENUM_VIOLATION,
                        details=f"Column '{col}' contains {enum_count} values outside allowed set.",
                        failed_rows_count=enum_count
                    ))

            # Regex pattern check
            if col_contract.pattern:
                regex_count = self.conn.execute(
                    f"SELECT COUNT(*) FROM target_data WHERE regexp_matches(CAST({col} AS VARCHAR), '{col_contract.pattern}') = false;"
                ).fetchone()[0]
                if regex_count > 0:
                    violations.append(Violation(
                        column=col,
                        violation_type=ViolationType.REGEX_VIOLATION,
                        details=f"Column '{col}' contains {regex_count} values violating regex pattern '{col_contract.pattern}'.",
                        failed_rows_count=regex_count
                    ))

        # 3. Custom SQL Quality Rules
        for rule in self.contract.quality_rules:
            fail_count = self.conn.execute(
                f"SELECT COUNT(*) FROM target_data WHERE NOT ({rule.sql});"
            ).fetchone()[0]
            if fail_count > 0:
                violations.append(Violation(
                    violation_type=ViolationType.QUALITY_RULE_FAILED,
                    details=f"Rule '{rule.name}' failed on {fail_count} rows: {rule.description or rule.sql}",
                    failed_rows_count=fail_count
                ))

        return ValidationResult(
            contract_name=f"{self.contract.dataset} (v{self.contract.version})",
            is_valid=(len(violations) == 0),
            total_rows_inspected=total_rows,
            violations=violations
        )

    def _is_compatible_type(self, observed: str, expected: str) -> bool:
        # Handles typical DuckDB type variants
        compat_groups = [
            {"VARCHAR", "TEXT", "STRING"},
            {"BIGINT", "INTEGER", "INT8", "INT4", "HUGEINT"},
            {"DOUBLE", "FLOAT", "DECIMAL"}
        ]
        for group in compat_groups:
            if observed in group and expected in group:
                return True
        return False