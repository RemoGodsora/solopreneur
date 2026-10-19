import asyncio
from dotenv import load_dotenv

load_dotenv()

from core.state import AgentState
from core.graph import build_operations_graph

# Sample invoice with $1,700 variance over PO-2026-901 ($12,500 approved)
HIGH_RISK_INVOICE = """
INVOICE #: INV-2026-0099
Vendor: CloudScale Hosting (ID: VEND_001)
Date: 2026-10-19
Currency: USD

Line Items:
- Dedicated Kubernetes Cluster Compute: $10,500.00
- Multi-region egress data transfer: $3,700.00

Subtotal: $14,200.00
Tax: $0.00
Total Amount: $14,200.00
PO Reference: PO-2026-901
"""

async def main():
    graph = build_operations_graph()
    
    state = AgentState(
        run_id="run_variance_002",
        raw_document_text=HIGH_RISK_INVOICE
    )
    
    print("\n--- Testing High-Risk Variance Workflow ---")
    result = await graph.ainvoke(state)
    
    print(f"Status:          {result['current_status']}")
    print(f"Risk Level:      {result['risk_level']}")
    print(f"Discrepancy:     ${result['discrepancy_amount']:.2f}")
    print(f"Approval Token:  {result.get('approval_token')}")
    print(f"Risk Reasons:    {result.get('risk_reasons')}")
    print(f"Audit Hash:      {result['final_audit_hash'][:16]}...\n")

if __name__ == "__main__":
    asyncio.run(main())