# v2_fb_cost Schema

**Table:** `sazoshop.firestore_collection.v2_fb_cost`
**Vendor:** FB (FastBox)

## Columns

| column_name | data_type |
|-------------|-----------|
| id | STRING |
| order_id | STRING |
| fb_id | STRING |
| master_id | STRING |
| shipping_type | STRING |
| shipping_number | STRING |
| chargeable_weight | FLOAT64 |
| chargeable_weight_range | FLOAT64 |
| delivery_fee_krw | FLOAT64 |
| etc_fee_krw | FLOAT64 |
| fuel_surcharge | FLOAT64 |
| net_delivery_fee_krw | FLOAT64 |
| tariff_krw | FLOAT64 |
| shipping_date | DATETIME |

## Comparison with KSE

| Feature | KSE | FB |
|---------|-----|-----|
| dimensions | ✅ YES | ❌ NO |
| actual_weight | ✅ YES | ❌ NO |
| volumetric_weight | ✅ YES | ❌ NO |
| chargeable_weight | ✅ YES | ✅ YES |

## Conclusion

**FB table cannot be used for weight/volume experiments** - it lacks the actual measurement data.

Only KSE data has the ground truth labels we need.
