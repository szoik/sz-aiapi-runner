# Dataset Field Origin Hierarchy

## Identifiers
* v2_order_items.order_item_order_id
  * v2_order_items.order_item_id
  * v2_order_items.order_item_product_id
  * v2_order_items.order_item_product_version_id

## Input Features - Text
* product_title_origin:  oid.order_item_title_origin → v2_order_items.order_item_title_origin
  * product_title_target:  oid.order_item_title_target → v2_order_items.order_item_title_target
* product_category:      oid.order_item_product_version_info_category → v2_order_items.order_item_product_version_info_category
* custom_category:       oid.order_item_meta_custom_category_name → v2_order_items.order_item_meta_custom_category_name
* site_name:             oid.order_item_product_version_site_name → v2_order_items.order_item_product_version_site_name
  * product_details:       oid.order_item_product_version_details → v2_order_items.order_item_product_version_details
* product_info_details:  oid.order_item_product_version_info_details → v2_order_items.order_item_product_version_info_details
* materials:             oid.order_item_meta_materials → v2_order_items.order_item_meta_materials
* clothing_materials:    oid.order_item_meta_clothing_materials → v2_order_items.order_item_meta_clothing_materials
* hscode:                oid.order_item_meta_hscode → v2_order_items.order_item_meta_hscode

## Input Features - Image
* thumbnail_urls:  oid.thumbnail_urls → ARRAY_TO_STRING(v2_order_items.order_item_product_version_thumbnail_urls, '|')
* thumbnail_count: oid.thumbnail_count → ARRAY_LENGTH(v2_order_items.order_item_product_version_thumbnail_urls)

## Input Features - Price
* price_origin: oid.order_item_price_origin_base → v2_order_items.order_item_price_origin_base
* price_krw:    oid.order_item_price_target_base → v2_order_items.order_item_price_target_base

## Input Features - URL
  * product_url: oid.order_item_product_version_url → v2_order_items.order_item_product_version_url

## Labels - Actual Measurements
* actual_weight_kg:    kse.actual_weight → v2_kse_cost.actual_weight
* actual_width_cm:     kse.width_cm → CAST(SPLIT(v2_kse_cost.dimensions, 'x')[0] AS FLOAT64)
* actual_length_cm:    kse.length_cm → CAST(SPLIT(v2_kse_cost.dimensions, 'x')[1] AS FLOAT64)
* actual_height_cm:    kse.height_cm → CAST(SPLIT(v2_kse_cost.dimensions, 'x')[2] AS FLOAT64)
* actual_volume_m3:    kse.volume_m3 → (width × length × height) / 1000000
* volumetric_weight_kg: kse.volumetric_weight → v2_kse_cost.volumetric_weight

## Metadata - AI Estimates
* ai_estimated_weight_kg:  oid.ai_estimated_weight_kg → JSON_EXTRACT_SCALAR(v2_order_items.order_item_product_version_extra, '$.weight')
* ai_estimated_volume_m3:  oid.ai_estimated_volume_m3 → JSON_EXTRACT_SCALAR(v2_order_items.order_item_product_version_extra, '$.volume')
* ai_estimated_width_cm:   oid.ai_estimated_width → JSON_EXTRACT_SCALAR(v2_order_items.order_item_product_version_extra, '$.width')
* ai_estimated_length_cm:  oid.ai_estimated_depth → JSON_EXTRACT_SCALAR(v2_order_items.order_item_product_version_extra, '$.depth')
* ai_estimated_height_cm:  oid.ai_estimated_height → JSON_EXTRACT_SCALAR(v2_order_items.order_item_product_version_extra, '$.height')
  * ai_calculated_volume_m3: (ai_estimated_width × ai_estimated_depth × ai_estimated_height) / 1000000
* weight_error_rate:       |ai_estimated_weight_kg - actual_weight| / actual_weight
* volume_error_rate:       |ai_estimated_volume_m3 - volume_m3| / volume_m3

## Metadata - Other
* shipping_date:    kse.shipping_date → v2_kse_cost.shipping_date
* order_created_at: oid.created_at → v2_order_items.created_at

---

# Dataset Compaction

## Identifiers
* v2_order_items.order_item_order_id

## Input Features - Text
* product_title_origin:  oid.order_item_title_origin → v2_order_items.order_item_title_origin
* product_category:      oid.order_item_product_version_info_category → v2_order_items.order_item_product_version_info_category
* hscode:                oid.order_item_meta_hscode → v2_order_items.order_item_meta_hscode

## Input Features - Image
* thumbnail_urls:  oid.thumbnail_urls → ARRAY_TO_STRING(v2_order_items.order_item_product_version_thumbnail_urls, '|')

## Labels - Actual Measurements
* actual_weight_kg:    kse.actual_weight → v2_kse_cost.actual_weight
* actual_width_cm:     kse.width_cm → CAST(SPLIT(v2_kse_cost.dimensions, 'x')[0] AS FLOAT64)
* actual_length_cm:    kse.length_cm → CAST(SPLIT(v2_kse_cost.dimensions, 'x')[1] AS FLOAT64)
* actual_height_cm:    kse.height_cm → CAST(SPLIT(v2_kse_cost.dimensions, 'x')[2] AS FLOAT64)
* actual_volume_m3:    kse.volume_m3 → (width × length × height) / 1000000
* volumetric_weight_kg: kse.volumetric_weight → v2_kse_cost.volumetric_weight

## Metadata - AI Estimates
* ai_estimated_weight_kg:  oid.ai_estimated_weight_kg → JSON_EXTRACT_SCALAR(v2_order_items.order_item_product_version_extra, '$.weight')
* ai_estimated_volume_m3:  oid.ai_estimated_volume_m3 → JSON_EXTRACT_SCALAR(v2_order_items.order_item_product_version_extra, '$.volume')
* ai_estimated_width_cm:   oid.ai_estimated_width → JSON_EXTRACT_SCALAR(v2_order_items.order_item_product_version_extra, '$.width')
* ai_estimated_length_cm:  oid.ai_estimated_depth → JSON_EXTRACT_SCALAR(v2_order_items.order_item_product_version_extra, '$.depth')
* ai_estimated_height_cm:  oid.ai_estimated_height → JSON_EXTRACT_SCALAR(v2_order_items.order_item_product_version_extra, '$.height')
  * ai_calculated_volume_m3: (ai_estimated_width × ai_estimated_depth × ai_estimated_height) / 1000000
* weight_error_rate:       |ai_estimated_weight_kg - actual_weight| / actual_weight
* volume_error_rate:       |ai_estimated_volume_m3 - volume_m3| / volume_m3

## Metadata - Other
* shipping_date:    kse.shipping_date → v2_kse_cost.shipping_date
* order_created_at: oid.created_at → v2_order_items.created_at
