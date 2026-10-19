import os
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from groq import AsyncGroq
from core.state import ExtractedInvoice

load_dotenv()

class InferenceEngine:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not set in environment or constructor.")
        self.client = AsyncGroq(api_key=self.api_key)

    async def extract_invoice(self, document_text: str) -> ExtractedInvoice:
        """Parses unstructured text into a validated Pydantic invoice schema."""
        system_prompt = (
            "You are an enterprise accounting parser. Extract the structured invoice data "
            "from the raw text. Return ONLY a valid JSON object matching this schema:\n"
            "{\n"
            '  "invoice_number": "string",\n'
            '  "vendor_id": "string",\n'
            '  "vendor_name": "string",\n'
            '  "invoice_date": "YYYY-MM-DD",\n'
            '  "currency": "USD",\n'
            '  "subtotal": 0.0,\n'
            '  "tax_amount": 0.0,\n'
            '  "total_amount": 0.0,\n'
            '  "line_items": [\n'
            '    {"item_id": "string", "description": "string", "quantity": 1.0, "unit_price": 0.0, "total_amount": 0.0}\n'
            "  ]\n"
            "}"
        )

        response = await self.client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Invoice text:\n{document_text}"}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        raw_json = json.loads(response.choices[0].message.content)
        return ExtractedInvoice.model_validate(raw_json)