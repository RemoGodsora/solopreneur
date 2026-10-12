from typing import List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field

class EnforcementLevel(str, Enum):
    STRICT = "strict"
    WARN = "warn"

class ColumnContract(BaseModel):
    name: str
    type: str  # DuckDB logical type: VARCHAR, BIGINT, DOUBLE, TIMESTAMP, etc.
    nullable: bool = True
    unique: bool = False
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[str]] = None
    pattern: Optional[str] = None

class QualityRule(BaseModel):
    name: str
    sql: str
    description: Optional[str] = None

class ContractSchema(BaseModel):
    columns: List[ColumnContract]

class DataContract(BaseModel):
    version: str
    dataset: str
    description: Optional[str] = None
    enforcement_level: EnforcementLevel = EnforcementLevel.STRICT
    schema_def: ContractSchema = Field(..., alias="schema")
    quality_rules: List[QualityRule] = Field(default_factory=list)

class ViolationType(str, Enum):
    MISSING_COLUMN = "MISSING_COLUMN"
    EXTRA_COLUMN = "EXTRA_COLUMN"
    TYPE_MISMATCH = "TYPE_MISMATCH"
    NULL_VIOLATION = "NULL_VIOLATION"
    UNIQUENESS_VIOLATION = "UNIQUENESS_VIOLATION"
    RANGE_VIOLATION = "RANGE_VIOLATION"
    ENUM_VIOLATION = "ENUM_VIOLATION"
    REGEX_VIOLATION = "REGEX_VIOLATION"
    QUALITY_RULE_FAILED = "QUALITY_RULE_FAILED"

class Violation(BaseModel):
    column: Optional[str] = None
    violation_type: ViolationType
    details: str
    failed_rows_count: int = 0
    sample_values: Optional[List[Any]] = None

class ValidationResult(BaseModel):
    contract_name: str
    is_valid: bool
    total_rows_inspected: int
    violations: List[Violation] = Field(default_factory=list)