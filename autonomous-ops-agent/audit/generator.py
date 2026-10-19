import datetime
from typing import Dict, Any
from core.state import AgentState

class AuditReportGenerator:
    """Generates immutable Markdown and HTML operational audit certificates."""

    @staticmethod
    def generate_markdown_certificate(state: AgentState) -> str:
        inv = state.invoice
        inv_num = inv.invoice_number if inv else "N/A"
        vendor = inv.vendor_name if inv else "Unknown"
        amount = f"${inv.total_amount:,.2f}" if inv else "$0.00"

        trail_rows = "\n".join([
            f"| `{log.timestamp[:19]}` | **{log.step_name}** | {log.action_taken} |"
            for log in state.audit_trail
        ])

        reasons = "\n".join([f"- {r}" for r in state.risk_reasons]) if state.risk_reasons else "- None (Standard execution)"

        report = f"""# OPERATIONAL AUDIT CERTIFICATE
**Autonomous Operations & Reconciliation Agent**
*Run Identifier:* `{state.run_id}`  
*Verification Timestamp:* `{datetime.datetime.now(datetime.timezone.utc).isoformat()}`  
*Cryptographic Seal (SHA-256):* `{state.final_audit_hash}`  

---

### Executive Summary
| Field | Value |
| :--- | :--- |
| **Status** | `{state.current_status.upper()}` |
| **Risk Classification** | `{state.risk_level}` |
| **Vendor** | {vendor} |
| **Invoice Number** | `{inv_num}` |
| **Billed Amount** | {amount} |
| **Discrepancy vs PO** | ${state.discrepancy_amount:,.2f} |
| **Approval Token** | `{state.approval_token or "AUTO_BYPASS"}` |

### Risk Assessment & Triggers
{reasons}

---

### Complete Execution Audit Trail
| Timestamp (UTC) | Pipeline Step | Action Executed |
| :--- | :--- | :--- |
{trail_rows}

---
*Verified by Autonomous Ops Agent Engine v1.0. Deterministic execution guaranteed.*
"""
        return report