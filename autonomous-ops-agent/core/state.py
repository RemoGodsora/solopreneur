from typing import Annotated, Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
import datetime

class LineItem(BaseModel):
    item_id: str
    description: str
    quantity: float
    unit_price: float
    total_amount: float

class ExtractedInvoice(BaseModel):
    invoice_number: str
    vendor_id: str
    vendor_name: str
    invoice_date: str
    currency: str = "USD"
    subtotal: float
    tax_amount: float
    total_amount: float
    line_items: List[LineItem] = Field(default_factory=list)

class AuditLogEntry(BaseModel):
    step_name: str
    timestamp: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    action_taken: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AgentState(BaseModel):
    """The complete execution memory of the autonomous operations agent."""
    run_id: str
    raw_document_text: str
    current_status: Literal[
        "initialized",
        "extracted",
        "verified",
        "pending_human_approval",
        "approved",
        "rejected",
        "reconciled",
        "failed"
    ] = "initialized"
    
    # Extracted document entity
    invoice: Optional[ExtractedInvoice] = None
    
    # Financial ledger verification metrics
    ledger_matched: bool = False
    discrepancy_amount: float = 0.0
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "LOW"
    risk_reasons: List[str] = Field(default_factory=list)
    
    # Operational routing & tools executed
    tools_executed: List[str] = Field(default_factory=list)
    audit_trail: List[AuditLogEntry] = Field(default_factory=list)
    
    # Human-in-the-loop state
    approval_token: Optional[str] = None
    approver_comments: Optional[str] = None
    final_audit_hash: Optional[str] = None