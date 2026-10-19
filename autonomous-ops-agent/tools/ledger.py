import duckdb
from typing import Dict, Any

class LedgerEngine:
    def __init__(self, db_path: str = ":memory:"):
        self.conn = duckdb.connect(db_path)
        self._init_mock_ledger()

    def _init_mock_ledger(self):
        """Seed pre-existing vendor database and purchase orders for cross-checking."""
        self.conn.execute("""
            CREATE TABLE vendors (
                vendor_id VARCHAR PRIMARY KEY,
                name VARCHAR,
                contracted_rate_limit DOUBLE,
                is_active BOOLEAN
            );
            
            INSERT INTO vendors VALUES 
            ('VEND_001', 'CloudScale Hosting', 15000.0, true),
            ('VEND_002', 'DataStream Logistics', 5000.0, true),
            ('VEND_003', 'Apex Staffing Solutions', 30000.0, false);

            CREATE TABLE purchase_orders (
                po_number VARCHAR PRIMARY KEY,
                vendor_id VARCHAR,
                approved_amount DOUBLE,
                status VARCHAR
            );

            INSERT INTO purchase_orders VALUES
            ('PO-2026-901', 'VEND_001', 12500.0, 'OPEN'),
            ('PO-2026-902', 'VEND_002', 4500.0, 'OPEN');
        """)

    def verify_invoice(self, vendor_id: str, total_amount: float) -> Dict[str, Any]:
        """Cross-checks an invoice against approved purchase orders and vendor status."""
        query = """
            SELECT 
                v.name,
                v.is_active,
                v.contracted_rate_limit,
                COALESCE(p.approved_amount, 0.0) AS po_amount,
                p.po_number
            FROM vendors v
            LEFT JOIN purchase_orders p 
                ON v.vendor_id = p.vendor_id AND p.status = 'OPEN'
            WHERE v.vendor_id = ?
        """
        result = self.conn.execute(query, [vendor_id]).fetchone()
        
        if not result:
            return {
                "matched": False,
                "reason": f"Unknown vendor ID '{vendor_id}' not present in internal vendor directory."
            }
        
        vendor_name, is_active, rate_limit, po_amount, po_number = result
        
        if not is_active:
            return {
                "matched": False,
                "reason": f"Vendor '{vendor_name}' is marked INACTIVE in internal ERP."
            }
        
        discrepancy = round(total_amount - po_amount, 2)
        
        return {
            "matched": True,
            "vendor_name": vendor_name,
            "po_number": po_number,
            "approved_amount": po_amount,
            "invoice_amount": total_amount,
            "discrepancy": discrepancy,
            "exceeds_po": discrepancy > 0,
            "exceeds_limit": total_amount > rate_limit
        }