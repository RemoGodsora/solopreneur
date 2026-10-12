import json
import re
from typing import Dict, List, Optional
from core.models import DataContract, ValidationResult, ViolationType

try:
    from groq import Groq
    from config import GROQ_API_KEY, GROQ_MODEL
    groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
except ImportError:
    groq_client = None
    GROQ_MODEL = "openai/gpt-oss-20b"

class SelfHealingEngine:
    def __init__(self, contract: DataContract):
        self.contract = contract

    def generate_healing_view(self, data_file: str, validation_result: ValidationResult) -> str:
        """
        Synthesizes an SQL View that transforms drifted/corrupted data
        into full compliance with the contract specification.
        """
        missing_cols = [
            v.column for v in validation_result.violations 
            if v.violation_type == ViolationType.MISSING_COLUMN and v.column
        ]
        extra_cols = [
            v.column for v in validation_result.violations 
            if v.violation_type == ViolationType.EXTRA_COLUMN and v.column
        ]

        # 1. Resolve Column Mappings (Missing -> Extra)
        column_mappings = self._resolve_column_mappings(missing_cols, extra_cols)

        # 2. Build Column Projection Expressions
        projections: List[str] = []
        where_clauses: List[str] = []

        expected_cols = {c.name: c for c in self.contract.schema_def.columns}

        for col_name, col_contract in expected_cols.items():
            source_col = column_mappings.get(col_name, col_name)

            # Handle Type Casting and Defaults
            expr = f"CAST({source_col} AS {col_contract.type})"

            # Handle Nullability Violations (COALESCE or filter)
            if not col_contract.nullable:
                if col_contract.type in ["VARCHAR", "TEXT", "STRING"]:
                    expr = f"COALESCE(NULLIF(TRIM(CAST({source_col} AS VARCHAR)), ''), 'N/A')"
                elif col_contract.type in ["BIGINT", "INTEGER"]:
                    default_val = col_contract.min_value if col_contract.min_value is not None else 0
                    expr = f"COALESCE(TRY_CAST({source_col} AS {col_contract.type}), {int(default_val)})"
                elif col_contract.type in ["DOUBLE", "FLOAT"]:
                    default_val = col_contract.min_value if col_contract.min_value is not None else 0.0
                    expr = f"COALESCE(TRY_CAST({source_col} AS {col_contract.type}), {float(default_val)})"

            # Handle Enum Constraints (Fallback mapping for unknown values)
            if col_contract.allowed_values:
                default_enum = col_contract.allowed_values[0]
                allowed_list = ", ".join([f"'{v}'" for v in col_contract.allowed_values])
                expr = f"CASE WHEN {source_col} IN ({allowed_list}) THEN {source_col} ELSE '{default_enum}' END"

            projections.append(f"    {expr} AS {col_name}")

        # 3. Handle Range/Sanity Bounds via SQL WHERE Filters
        for col_contract in self.contract.schema_def.columns:
            source_col = column_mappings.get(col_contract.name, col_contract.name)
            if col_contract.min_value is not None:
                where_clauses.append(f"TRY_CAST({source_col} AS {col_contract.type}) >= {col_contract.min_value}")

        # 4. Assemble the Self-Healing View SQL
        projection_sql = ",\n".join(projections)
        where_sql = f"\nWHERE\n    " + " AND\n    ".join(where_clauses) if where_clauses else ""

        view_sql = f"""-- Auto-Generated Self-Healing Adapter by SchemaSentinel
-- Dataset: {self.contract.dataset} (Target Contract v{self.contract.version})
CREATE OR REPLACE VIEW v_{self.contract.dataset}_healed AS
SELECT
{projection_sql}
FROM read_csv_auto('{data_file}'){where_sql};
"""
        return view_sql

    def _resolve_column_mappings(self, missing_cols: List[str], extra_cols: List[str]) -> Dict[str, str]:
        """Maps missing required contract columns to extra incoming drifted columns."""
        mappings: Dict[str, str] = {}
        if not missing_cols or not extra_cols:
            return mappings

        # Attempt AI semantic mapping if Groq is available
        if groq_client:
            try:
                prompt = (
                    f"Match missing columns {missing_cols} to observed drifted columns {extra_cols}. "
                    "Return ONLY JSON: {\"missing_col\": \"drifted_col\"}. No markdown or extra text."
                )
                res = groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=100
                )
                raw_json = re.sub(r"^```(?:json)?\s*|\s*```$", "", res.choices[0].message.content.strip())
                parsed = json.loads(raw_json)
                return {k: v for k, v in parsed.items() if k in missing_cols and v in extra_cols}
            except Exception:
                pass

        # Deterministic Heuristic Fallback (substring / prefix matching)
        for m in missing_cols:
            m_core = m.replace("_id", "").replace("id", "").lower()
            for e in extra_cols:
                e_core = e.replace("_uuid", "").replace("_id", "").replace("id", "").lower()
                if m_core in e_core or e_core in m_core or "user" in e and "cust" in m:
                    mappings[m] = e
                    break
        return mappings