import os
import uuid
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

from core.state import AgentState, AuditLogEntry
from core.graph import build_operations_graph
from audit.generator import AuditReportGenerator

app = FastAPI(
    title="Autonomous Operations & Audit Gateway",
    version="1.0.0",
    description="Enterprise reconciliation agent with deterministic human-in-the-loop pause gates."
)

graph = build_operations_graph()

# In-memory execution state store for running agent instances
STATE_STORE: Dict[str, Dict[str, Any]] = {}

class InvoiceSubmission(BaseModel):
    document_text: str = Field(..., min_length=20)

class HumanApprovalPayload(BaseModel):
    approval_token: str
    action: str = Field(..., pattern="^(approve|reject)$")
    operator_notes: Optional[str] = "Approved via operational dashboard"

@app.post("/api/v1/operations/submit", status_code=status.HTTP_200_OK, tags=["Agent Operations"])
async def submit_invoice_for_reconciliation(payload: InvoiceSubmission):
    run_id = f"ops-{uuid.uuid4().hex[:8]}"
    
    initial_state = AgentState(
        run_id=run_id,
        raw_document_text=payload.document_text
    )
    
    result = await graph.ainvoke(initial_state)
    STATE_STORE[run_id] = result
    
    return {
        "run_id": run_id,
        "status": result["current_status"],
        "risk_level": result["risk_level"],
        "discrepancy_amount": result["discrepancy_amount"],
        "approval_token": result.get("approval_token"),
        "audit_hash": result.get("final_audit_hash")
    }

@app.post("/api/v1/operations/review/{run_id}", tags=["Human-in-the-Loop"])
async def review_human_approval(run_id: str, payload: HumanApprovalPayload):
    if run_id not in STATE_STORE:
        raise HTTPException(status_code=404, detail="Operation run ID not found.")
    
    current_run = STATE_STORE[run_id]
    
    if current_run["current_status"] != "pending_human_approval":
        raise HTTPException(
            status_code=400, 
            detail=f"Operation is in state '{current_run['current_status']}', not awaiting approval."
        )
    
    if current_run.get("approval_token") != payload.approval_token:
        raise HTTPException(status_code=403, detail="Invalid approval token.")
    
    # Resume pipeline after operator signoff
    new_status = "reconciled" if payload.action == "approve" else "rejected"
    log = AuditLogEntry(
        step_name="human_operator_review",
        action_taken=f"Operator marked run as {new_status.upper()}: {payload.operator_notes}",
        metadata={"operator_notes": payload.operator_notes}
    )
    
    current_run["current_status"] = new_status
    current_run["audit_trail"].append(log)
    STATE_STORE[run_id] = current_run
    
    return {
        "run_id": run_id,
        "status": new_status,
        "message": f"Human-in-the-loop decision applied: {new_status}."
    }

@app.get("/api/v1/operations/certificate/{run_id}", tags=["Audit & Governance"])
async def get_audit_certificate(run_id: str):
    if run_id not in STATE_STORE:
        raise HTTPException(status_code=404, detail="Operation run ID not found.")
    
    state_obj = AgentState.model_validate(STATE_STORE[run_id])
    certificate_md = AuditReportGenerator.generate_markdown_certificate(state_obj)
    
    return {
        "run_id": run_id,
        "audit_hash": state_obj.final_audit_hash,
        "certificate_markdown": certificate_md
    }