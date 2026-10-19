import pytest
from dotenv import load_dotenv

load_dotenv()

from core.state import AgentState
from core.graph import build_operations_graph

@pytest.mark.asyncio
async def test_low_risk_auto_reconciliation():
    graph = build_operations_graph()
    
    invoice_text = """
    INVOICE #: INV-TEST-001
    Vendor: CloudScale Hosting (ID: VEND_001)
    Date: 2026-10-20
    Currency: USD
    Subtotal: $12,500.00
    Tax: $0.00
    Total Amount: $12,500.00
    PO Reference: PO-2026-901
    """
    
    state = AgentState(run_id="test_low_001", raw_document_text=invoice_text)
    result = await graph.ainvoke(state)
    
    assert result["current_status"] == "reconciled"
    assert result["risk_level"] == "LOW"
    assert result["discrepancy_amount"] == 0.0
    assert result["final_audit_hash"] is not None

@pytest.mark.asyncio
async def test_high_risk_pause_gate():
    graph = build_operations_graph()
    
    invoice_text = """
    INVOICE #: INV-TEST-002
    Vendor: CloudScale Hosting (ID: VEND_001)
    Date: 2026-10-20
    Currency: USD
    Subtotal: $14,200.00
    Tax: $0.00
    Total Amount: $14,200.00
    PO Reference: PO-2026-901
    """
    
    state = AgentState(run_id="test_high_002", raw_document_text=invoice_text)
    result = await graph.ainvoke(state)
    
    assert result["current_status"] == "pending_human_approval"
    assert result["risk_level"] == "HIGH"
    assert result["discrepancy_amount"] == 1700.0
    assert result["approval_token"].startswith("AUTH-")
    assert result["final_audit_hash"] is not None