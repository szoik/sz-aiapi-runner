-- Experiment Sample Selection
-- Compare actual vs AI estimated: weight, volume, and individual dimensions (sorted)
-- 
-- Key insight: Volume can hide errors (1x20x1 vs 2x5x2 = same volume, different shape)
-- Solution: Sort dimensions and compare L/W/H individually

WITH single_item_orders AS (
  SELECT order_item_order_id
  FROM `sazoshop.firestore_snapshot.v2_order_items`
  GROUP BY order_item_order_id
  HAVING COUNT(DISTINCT order_item_id) = 1
),

base_data AS (
  SELECT
    oi.order_item_order_id,
    oi.order_item_title_origin AS title,
    oi.order_item_product_version_info_category AS category,
    ARRAY_TO_STRING(oi.order_item_product_version_thumbnail_urls, '|') AS thumbnail_urls,
    
    -- Actual measurements (from KSE)
    kse.actual_weight,
    CAST(SPLIT(kse.dimensions, 'x')[OFFSET(0)] AS FLOAT64) AS actual_d1,
    CAST(SPLIT(kse.dimensions, 'x')[OFFSET(1)] AS FLOAT64) AS actual_d2,
    CAST(SPLIT(kse.dimensions, 'x')[OFFSET(2)] AS FLOAT64) AS actual_d3,
    kse.dimensions AS actual_dimensions_raw,
    
    -- AI estimated measurements
    SAFE_CAST(JSON_EXTRACT_SCALAR(oi.order_item_product_version_extra, '$.weight') AS FLOAT64) AS ai_weight,
    SAFE_CAST(JSON_EXTRACT_SCALAR(oi.order_item_product_version_extra, '$.width') AS FLOAT64) AS ai_d1,
    SAFE_CAST(JSON_EXTRACT_SCALAR(oi.order_item_product_version_extra, '$.depth') AS FLOAT64) AS ai_d2,
    SAFE_CAST(JSON_EXTRACT_SCALAR(oi.order_item_product_version_extra, '$.height') AS FLOAT64) AS ai_d3,
    SAFE_CAST(JSON_EXTRACT_SCALAR(oi.order_item_product_version_extra, '$.volume') AS FLOAT64) AS ai_volume,
    
    kse.shipping_date
    
  FROM `sazoshop.firestore_snapshot.v2_order_items` oi
  INNER JOIN `sazoshop.firestore_collection.v2_kse_cost` kse
    ON oi.order_item_order_id = kse.order_id
  WHERE 
    oi.order_item_order_id IN (SELECT order_item_order_id FROM single_item_orders)
    AND kse.dimensions IS NOT NULL
    AND kse.actual_weight IS NOT NULL
    AND kse.actual_weight > 0
    AND kse.actual_weight < 100
    AND REGEXP_CONTAINS(kse.dimensions, r'^[0-9.]+x[0-9.]+x[0-9.]+$')
    AND oi.order_item_title_origin IS NOT NULL
    -- Must have AI estimates to compare
    AND JSON_EXTRACT_SCALAR(oi.order_item_product_version_extra, '$.weight') IS NOT NULL
),

sorted_dimensions AS (
  SELECT
    *,
    -- Sort actual dimensions (descending: L >= W >= H)
    GREATEST(actual_d1, actual_d2, actual_d3) AS actual_L,
    -- Middle value
    (actual_d1 + actual_d2 + actual_d3) 
      - GREATEST(actual_d1, actual_d2, actual_d3) 
      - LEAST(actual_d1, actual_d2, actual_d3) AS actual_W,
    LEAST(actual_d1, actual_d2, actual_d3) AS actual_H,
    
    -- Sort AI dimensions (descending: L >= W >= H)
    GREATEST(IFNULL(ai_d1,0), IFNULL(ai_d2,0), IFNULL(ai_d3,0)) AS ai_L,
    (IFNULL(ai_d1,0) + IFNULL(ai_d2,0) + IFNULL(ai_d3,0)) 
      - GREATEST(IFNULL(ai_d1,0), IFNULL(ai_d2,0), IFNULL(ai_d3,0)) 
      - LEAST(IFNULL(ai_d1,0), IFNULL(ai_d2,0), IFNULL(ai_d3,0)) AS ai_W,
    LEAST(IFNULL(ai_d1,0), IFNULL(ai_d2,0), IFNULL(ai_d3,0)) AS ai_H,
    
    -- Calculate volumes
    (actual_d1 * actual_d2 * actual_d3) / 1000000 AS actual_volume_m3,
    (IFNULL(ai_d1,0) * IFNULL(ai_d2,0) * IFNULL(ai_d3,0)) / 1000000 AS ai_calc_volume_m3
    
  FROM base_data
),

with_errors AS (
  SELECT
    *,
    -- Weight error
    CASE WHEN actual_weight > 0 
      THEN ABS(ai_weight - actual_weight) / actual_weight 
      ELSE NULL END AS weight_error,
    
    -- Volume error
    CASE WHEN actual_volume_m3 > 0 
      THEN ABS(ai_calc_volume_m3 - actual_volume_m3) / actual_volume_m3 
      ELSE NULL END AS volume_error,
    
    -- Individual dimension errors (sorted)
    CASE WHEN actual_L > 0 
      THEN ABS(ai_L - actual_L) / actual_L 
      ELSE NULL END AS L_error,
    CASE WHEN actual_W > 0 
      THEN ABS(ai_W - actual_W) / actual_W 
      ELSE NULL END AS W_error,
    CASE WHEN actual_H > 0 
      THEN ABS(ai_H - actual_H) / actual_H 
      ELSE NULL END AS H_error,
    
    -- Combined dimension error (average of L/W/H errors)
    (
      CASE WHEN actual_L > 0 THEN ABS(ai_L - actual_L) / actual_L ELSE 0 END +
      CASE WHEN actual_W > 0 THEN ABS(ai_W - actual_W) / actual_W ELSE 0 END +
      CASE WHEN actual_H > 0 THEN ABS(ai_H - actual_H) / actual_H ELSE 0 END
    ) / 3 AS avg_dimension_error
    
  FROM sorted_dimensions
  WHERE ai_d1 IS NOT NULL  -- Has dimension estimates
)

SELECT
  order_item_order_id,
  title,
  category,
  thumbnail_urls,
  
  -- Actual (sorted)
  actual_weight,
  CONCAT(CAST(actual_L AS STRING), 'x', CAST(actual_W AS STRING), 'x', CAST(actual_H AS STRING)) AS actual_LWH,
  ROUND(actual_volume_m3, 6) AS actual_volume_m3,
  
  -- AI estimated (sorted)
  ai_weight,
  CONCAT(CAST(ai_L AS STRING), 'x', CAST(ai_W AS STRING), 'x', CAST(ai_H AS STRING)) AS ai_LWH,
  ROUND(ai_calc_volume_m3, 6) AS ai_volume_m3,
  
  -- Errors
  ROUND(weight_error, 3) AS weight_error,
  ROUND(volume_error, 3) AS volume_error,
  ROUND(L_error, 3) AS L_error,
  ROUND(W_error, 3) AS W_error,
  ROUND(H_error, 3) AS H_error,
  ROUND(avg_dimension_error, 3) AS avg_dim_error,
  
  -- Error category
  CASE
    WHEN weight_error >= 1.0 THEN 'weight_over_100pct'
    WHEN weight_error >= 0.5 THEN 'weight_50_100pct'
    ELSE 'weight_under_50pct'
  END AS weight_error_category,
  
  CASE
    WHEN volume_error >= 1.0 THEN 'volume_over_100pct'
    WHEN volume_error >= 0.5 THEN 'volume_50_100pct'
    ELSE 'volume_under_50pct'
  END AS volume_error_category,
  
  CASE
    WHEN avg_dimension_error >= 1.0 THEN 'dim_over_100pct'
    WHEN avg_dimension_error >= 0.5 THEN 'dim_50_100pct'
    ELSE 'dim_under_50pct'
  END AS dimension_error_category,
  
  shipping_date

FROM with_errors
ORDER BY shipping_date DESC;


-- ============================================================
-- SAMPLE QUERIES FOR EXPERIMENT SETS
-- ============================================================

-- [Query A] High weight error (0.5 ~ 1.0)
-- SELECT * FROM above_query WHERE weight_error >= 0.5 AND weight_error < 1.0 LIMIT 50;

-- [Query B] Very high weight error (> 1.0)
-- SELECT * FROM above_query WHERE weight_error >= 1.0 LIMIT 50;

-- [Query C] High volume error (0.5 ~ 1.0)
-- SELECT * FROM above_query WHERE volume_error >= 0.5 AND volume_error < 1.0 LIMIT 50;

-- [Query D] Very high volume error (> 1.0)
-- SELECT * FROM above_query WHERE volume_error >= 1.0 LIMIT 50;

-- [Query E] High dimension error (0.5 ~ 1.0)
-- SELECT * FROM above_query WHERE avg_dimension_error >= 0.5 AND avg_dimension_error < 1.0 LIMIT 50;

-- [Query F] Very high dimension error (> 1.0)
-- SELECT * FROM above_query WHERE avg_dimension_error >= 1.0 LIMIT 50;
