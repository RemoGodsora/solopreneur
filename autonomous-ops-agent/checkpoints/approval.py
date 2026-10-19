import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class ApprovalRecord(BaseModel):
    run_id: str
    approval_token: str
    created_at: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED
    operator_notes: Optional[str] = None
    resolved_at: Optional[str] = None

class ApprovalManager:
    """In-memory thread-safe checkpoint manager for operational pause gates."""
    
    def __init__(self):
        self._records: Dict[str, ApprovalRecord] = {}

    def register_pause_gate(self, run_id: str, approval_token: str) -> ApprovalRecord:
        record = ApprovalRecord(run_id=run_id, approval_token=approval_token)
        self._records[run_id] = record
        return record

    def verify_and_resolve(
        self, run_id: str, approval_token: str, action: str, notes: Optional[str] = None
    ) -> bool:
        record = self._records.get(run_id)
        if not record or record.status != "PENDING":
            return False
        
        if record.approval_token != approval_token:
            return False

        record.status = "APPROVED" if action.lower() == "approve" else "REJECTED"
        record.operator_notes = notes
        record.resolved_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return True

    def get_record(self, run_id: str) -> Optional[ApprovalRecord]:
        return self._records.get(run_id)