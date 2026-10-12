-- Auto-Generated Self-Healing Adapter by SchemaSentinel
-- Dataset: orders (Target Contract v1.0.0)
CREATE OR REPLACE VIEW v_orders_healed AS
SELECT
    COALESCE(NULLIF(TRIM(CAST(order_id AS VARCHAR)), ''), 'N/A') AS order_id,
    COALESCE(NULLIF(TRIM(CAST(user_uuid AS VARCHAR)), ''), 'N/A') AS customer_id,
    CAST(order_timestamp AS TIMESTAMP) AS order_timestamp,
    CASE WHEN status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'CANCELLED') THEN status ELSE 'PENDING' END AS status,
    COALESCE(TRY_CAST(item_count AS BIGINT), 1) AS item_count,
    COALESCE(TRY_CAST(order_total AS DOUBLE), 0.01) AS order_total
FROM read_csv_auto('data/orders_corrupted.csv')
WHERE
    TRY_CAST(item_count AS BIGINT) >= 1.0 AND
    TRY_CAST(order_total AS DOUBLE) >= 0.01;
