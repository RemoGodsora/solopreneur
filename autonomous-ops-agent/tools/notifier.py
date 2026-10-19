import os
import httpx
from typing import Optional, Dict, Any

class ApprovalNotifier:
    """Dispatches real-time review requests to operational webhook channels."""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("DISCORD_SLACK_WEBHOOK_URL")

    async def send_approval_request(
        self,
        run_id: str,
        vendor_name: str,
        invoice_number: str,
        invoice_amount: float,
        discrepancy: float,
        approval_token: str,
        risk_reasons: list[str]
    ) -> bool:
        """Sends an operational approval alert with review token and actions."""
        if not self.webhook_url:
            print(f"[Notifier Bypass] No webhook URL configured. Token for {run_id}: {approval_token}")
            return False

        reasons_text = "\n".join([f"• {r}" for r in risk_reasons])
        
        # Discord / Slack compatible embed payload
        payload = {
            "content": f"🚨 **OPERATIONAL RECONCILIATION HALTED** — `Run ID: {run_id}`",
            "embeds": [
                {
                    "title": "Human-in-the-Loop Review Required",
                    "color": 15158332,  # Crimson Red
                    "fields": [
                        {"name": "Vendor", "value": vendor_name, "inline": True},
                        {"name": "Invoice #", "value": invoice_number, "inline": True},
                        {"name": "Billed Amount", "value": f"${invoice_amount:,.2f}", "inline": True},
                        {"name": "PO Discrepancy", "value": f"+${discrepancy:,.2f}", "inline": True},
                        {"name": "Risk Classification", "value": "HIGH / CRITICAL", "inline": True},
                        {"name": "Authorization Token", "value": f"`{approval_token}`", "inline": False},
                        {"name": "Flagged Reasons", "value": reasons_text or "Manual review required", "inline": False},
                    ],
                    "footer": {
                        "text": f"Submit POST to /api/v1/operations/review/{run_id} with token to approve/reject."
                    }
                }
            ]
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(self.webhook_url, json=payload)
                return res.status_code in [200, 204]
        except Exception as e:
            print(f"[Notifier Error] Failed to dispatch webhook: {e}")
            return False