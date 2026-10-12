import csv
from datetime import datetime, timezone

def generate_valid_orders(filepath: str, count: int = 500):
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["order_id", "customer_id", "order_timestamp", "status", "item_count", "order_total"])
        for i in range(1, count + 1):
            writer.writerow([
                f"ORD-{i:05d}",
                f"CUST-{1000 + (i % 50)}",
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "COMPLETED" if i % 2 == 0 else "PENDING",
                (i % 5) + 1,
                round(((i % 5) + 1) * 19.99, 2)
            ])

def generate_drifted_orders(filepath: str, count: int = 500):
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Breaches injected:
        # 1. Renamed column: `customer_id` -> `user_uuid`
        # 2. Injected NULLs into non-nullable order_id
        # 3. Invalid enum value ('REFUNDED_PENDING')
        # 4. Item count 0 and negative order totals
        writer.writerow(["order_id", "user_uuid", "order_timestamp", "status", "item_count", "order_total", "legacy_notes"])
        for i in range(1, count + 1):
            order_id = "" if i == 10 else f"ORD-{i:05d}"
            status = "REFUNDED_PENDING" if i % 15 == 0 else "COMPLETED"
            items = 0 if i == 5 else (i % 5) + 1
            total = -10.0 if i == 20 else round(items * 15.50, 2)
            
            writer.writerow([
                order_id,
                f"USR-{2000 + i}",
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                status,
                items,
                total,
                "Auto-generated debug note"
            ])

if __name__ == "__main__":
    generate_valid_orders("data/orders_clean.csv")
    generate_drifted_orders("data/orders_corrupted.csv")
    print("Generated data/orders_clean.csv and data/orders_corrupted.csv")