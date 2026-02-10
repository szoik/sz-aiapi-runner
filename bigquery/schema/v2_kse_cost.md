# v2_kse_cost Schema

**Table:** `sazoshop.firestore_collection.v2_kse_cost`
**Vendor:** KSE (KokuSai Express)

## Columns

| column_name | data_type |
|-------------|-----------|
| id | STRING |
| order_id | STRING |
| kse_id | STRING |
| master_id | STRING |
| currency | STRING |
| dimensions | STRING |
| product_name | STRING |
| shipping_number | STRING |
| shipping_type | STRING |
| memo | STRING |
| delivery_fee | FLOAT64 |
| total_price | FLOAT64 |
| actual_weight | FLOAT64 |
| chargeable_weight | FLOAT64 |
| delivery_fee_krw | FLOAT64 |
| exchange_rate | FLOAT64 |
| volumetric_weight | FLOAT64 |
| etc_fee | FLOAT64 |
| etc_fee_krw | FLOAT64 |
| tariff | FLOAT64 |
| tariff_exchange_rate | FLOAT64 |
| tariff_krw | FLOAT64 |
| shipping_date | DATETIME |

## Key Columns for Experiment

| Column | Purpose |
|--------|---------|
| `order_id` | Join key to v2_order_items |
| `dimensions` | Actual dimensions (format: "WxLxH") |
| `actual_weight` | Actual measured weight (kg) |
| `volumetric_weight` | Volumetric weight (kg) |
| `shipping_date` | When shipped |
