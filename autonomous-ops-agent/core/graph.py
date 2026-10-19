import hashlib
import json
import uuid
from typing import Dict, Any
from langgraph.graph import StateGraph, START, END

from core.state import AgentState, AuditLogEntry
from core.engine import InferenceEngine
from tools.ledger import LedgerEngine
from tools.notifier import ApprovalNotifier

inference_engine = InferenceEngine()
ledger_engine = LedgerEngine()
notifier = ApprovalNotifier()

# ==============================================================================
# 1. GRAPH NODES
# ==============================================================================

async def extract_node(state: AgentState) -> Dict[str, Any]:
    """Node 1: Extract structured invoice data from unstructured document text."""
    invoice = await inference_engine.extract_invoice(state.raw_document_text)
    
    log = AuditLogEntry(
        step_name="document_extraction",
        action_taken=f"Extracted invoice {invoice.invoice_number} from vendor {invoice.vendor_name}",
        metadata={"invoice_number": invoice.invoice_number, "total": invoice.total_amount}
    )
    
    return {
        "invoice": invoice,
        "current_status": "extracted",
        "audit_trail": state.audit_trail + [log]
    }

async def ledger_cross_check_node(state: AgentState) -> Dict[str, Any]:
    """Node 2: Verify extracted invoice against internal DuckDB vendor & PO ledgers."""
    if not state.invoice:
        raise ValueError("Invoice not extracted before ledger cross-check.")
    
    check_result = ledger_engine.verify_invoice(
        vendor_id=state.invoice.vendor_id,
        total_amount=state.invoice.total_amount
    )
    
    tools = state.tools_executed + ["ledger_engine.verify_invoice"]
    log = AuditLogEntry(
        step_name="ledger_verification",
        action_taken="Cross-checked PO and rate limits in DuckDB",
        metadata=check_result
    )
    
    if not check_result.get("matched", False):
        return {
            "ledger_matched": False,
            "discrepancy_amount": state.invoice.total_amount,
            "risk_level": "CRITICAL",
            "risk_reasons": [check_result.get("reason", "Vendor mismatch")],
            "tools_executed": tools,
            "audit_trail": state.audit_trail + [log]
        }
    
    return {
        "ledger_matched": True,
        "discrepancy_amount": check_result.get("discrepancy", 0.0),
        "tools_executed": tools,
        "audit_trail": state.audit_trail + [log]
    }

async def risk_evaluation_node(state: AgentState) -> Dict[str, Any]:
    """Node 3: Assess operational risk based on variance, limit breaches, and discrepancies."""
    reasons = list(state.risk_reasons)
    risk = "LOW"
    
    # Financial reconciliation boundaries
    if not state.ledger_matched:
        risk = "CRITICAL"
    elif state.discrepancy_amount > 500.0:
        risk = "HIGH"
        reasons.append(f"Invoice exceeds Purchase Order by ${state.discrepancy_amount:.2f}")
    elif state.discrepancy_amount > 0.0:
        risk = "MEDIUM"
        reasons.append(f"Minor PO variance of ${state.discrepancy_amount:.2f}")
    
    log = AuditLogEntry(
        step_name="risk_assessment",
        action_taken=f"Calculated risk classification as {risk}",
        metadata={"risk_level": risk, "reasons": reasons}
    )
    
    return {
        "risk_level": risk,
        "risk_reasons": reasons,
        "current_status": "verified",
        "audit_trail": state.audit_trail + [log]
    }

async def auto_reconcile_node(state: AgentState) -> Dict[str, Any]:
    """Node 4A: Automatically reconcile low-risk operational entries."""
    log = AuditLogEntry(
        step_name="automated_reconciliation",
        action_taken="Committed invoice reconciliation directly to ledger",
        metadata={"auto_approved": True}
    )
    return {
        "current_status": "reconciled",
        "audit_trail": state.audit_trail + [log]
    }

async def human_pause_gate_node(state: AgentState) -> Dict[str, Any]:
    """Node 4B: Deterministic human-in-the-loop pause barrier for high-risk variances."""
    token = f"AUTH-{uuid.uuid4().hex[:12].upper()}"

    # Dispatch alert via webhook to team channel
    inv = state.invoice
    await notifier.send_approval_request(
        run_id=state.run_id,
        vendor_name=inv.vendor_name if inv else "Unknown",
        invoice_number=inv.invoice_number if inv else "N/A",
        invoice_amount=inv.total_amount if inv else 0.0,
        discrepancy=state.discrepancy_amount,
        approval_token=token,
        risk_reasons=state.risk_reasons
    )

    log = AuditLogEntry(
        step_name="human_in_the_loop_checkpoint",
        action_taken="Halted pipeline. Dispatched notification and awaiting authorized operator signature",
        metadata={"approval_token": token, "risk_reasons": state.risk_reasons}
    )
    return {
        "current_status": "pending_human_approval",
        "approval_token": token,
        "audit_trail": state.audit_trail + [log]
    }

async def audit_signing_node(state: AgentState) -> Dict[str, Any]:
    """Node 5: Generate permanent deterministic cryptographic SHA-256 seal of the run."""
    serialized_trail = json.dumps([entry.model_dump() for entry in state.audit_trail], sort_keys=True)
    run_hash = hashlib.sha256(serialized_trail.encode("utf-8")).hexdigest()
    
    return {
        "final_audit_hash": run_hash
    }

# ==============================================================================
# 2. CONDITIONAL ROUTING & GRAPH DEFINITION
# ==============================================================================

def route_risk(state: AgentState) -> str:
    """Evaluates whether to auto-commit or pause for human approval."""
    if state.risk_level in ["HIGH", "CRITICAL"]:
        return "human_pause_gate"
    return "auto_reconcile"

def build_operations_graph() -> StateGraph:
    workflow = StateGraph(AgentState)
    
    workflow.add_node("extract", extract_node)
    workflow.add_node("cross_check", ledger_cross_check_node)
    workflow.add_node("evaluate_risk", risk_evaluation_node)
    workflow.add_node("auto_reconcile", auto_reconcile_node)
    workflow.add_node("human_pause_gate", human_pause_gate_node)
    workflow.add_node("audit_sign", audit_signing_node)
    
    # Linear ingestion chain
    workflow.add_edge(START, "extract")
    workflow.add_edge("extract", "cross_check")
    workflow.add_edge("cross_check", "evaluate_risk")
    
    # Conditional branching
    workflow.add_conditional_edges(
        "evaluate_risk",
        route_risk,
        {
            "auto_reconcile": "auto_reconcile",
            "human_pause_gate": "human_pause_gate"
        }
    )
    
    # Convergence on final audit signing
    workflow.add_edge("auto_reconcile", "audit_sign")
    workflow.add_edge("human_pause_gate", "audit_sign")
    workflow.add_edge("audit_sign", END)
    
    return workflow.compile()