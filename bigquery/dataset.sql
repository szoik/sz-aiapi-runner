WITH single_item_orders AS (            -- 단일 아이템 주문만 선택
  SELECT
    oi.order_item_order_id,
    COUNT(DISTINCT oi.order_item_id) as item_count
  FROM `sazoshop.firestore_snapshot.v2_order_items` oi
  GROUP BY oi.order_item_order_id
  HAVING COUNT(DISTINCT oi.order_item_id) = 1
),

kse_shipping_data AS (                  -- KSE 실제 배송 데이터 (dimensions: 58.0x24.0x20.0 형식)
  SELECT
    kse.order_id,
    kse.dimensions,
    kse.actual_weight,
    kse.volumetric_weight,
    kse.shipping_date,
    -- dimensions 파싱
    CAST(SPLIT(dimensions, 'x')[OFFSET(0)] AS FLOAT64) AS width_cm,
    CAST(SPLIT(dimensions, 'x')[OFFSET(1)] AS FLOAT64) AS length_cm,
    CAST(SPLIT(dimensions, 'x')[OFFSET(2)] AS FLOAT64) AS height_cm,
    -- 부피 계산 (cm³ -> m³로 변환)
    (CAST(SPLIT(dimensions, 'x')[OFFSET(0)] AS FLOAT64) *
     CAST(SPLIT(dimensions, 'x')[OFFSET(1)] AS FLOAT64) *
     CAST(SPLIT(dimensions, 'x')[OFFSET(2)] AS FLOAT64)) / 1000000 AS volume_m3
  FROM `sazoshop.firestore_collection.v2_kse_cost` kse
  WHERE kse.order_id IN (SELECT order_item_order_id FROM single_item_orders)
    AND kse.dimensions IS NOT NULL
    AND kse.actual_weight IS NOT NULL
    AND kse.actual_weight > 0
    AND REGEXP_CONTAINS(kse.dimensions, r'^\d+\.?\d*x\d+\.?\d*x\d+\.?\d*$')  -- 유효한 형식만
),

order_item_details AS (             -- 주문 아이템 상세 정보 (order_id당 최신 1개만)
  SELECT
    oi.order_item_order_id,
    oi.order_item_id,
    oi.order_item_product_id,
    oi.order_item_product_version_id,

    -- [INPUT FEATURES] 상품 텍스트 정보
    oi.order_item_title_origin,
    oi.order_item_title_target,
    oi.order_item_product_version_info_category,
    oi.order_item_meta_custom_category_name,
    oi.order_item_product_version_site_name,

    -- [INPUT FEATURES] 상품 상세 정보
    oi.order_item_product_version_details,
    oi.order_item_product_version_info_details,

    -- [INPUT FEATURES] 재질 및 구성 정보
    oi.order_item_meta_materials,
    oi.order_item_meta_clothing_materials,
    oi.order_item_meta_hscode,

    -- [INPUT FEATURES] 이미지 정보
    ARRAY_TO_STRING(oi.order_item_product_version_thumbnail_urls, '|') AS thumbnail_urls,
    ARRAY_LENGTH(oi.order_item_product_version_thumbnail_urls) AS thumbnail_count,

    -- [INPUT FEATURES] 가격 정보 (간접 지표)
    oi.order_item_price_origin_base,
    oi.order_item_price_target_base,

    -- [INPUT FEATURES] 상품 URL
    oi.order_item_product_version_url,

    -- 기존 AI 추정값 (비교용)
    SAFE_CAST(JSON_EXTRACT_SCALAR(oi.order_item_product_version_extra, '$.weight') AS FLOAT64) AS ai_estimated_weight_kg,
    SAFE_CAST(JSON_EXTRACT_SCALAR(oi.order_item_product_version_extra, '$.volume') AS FLOAT64) AS ai_estimated_volume_m3,

    -- 추정 dimensions (JSON에서 추출 - 있는 경우)
    JSON_EXTRACT_SCALAR(oi.order_item_product_version_extra, '$.width') AS ai_estimated_width,
    JSON_EXTRACT_SCALAR(oi.order_item_product_version_extra, '$.depth') AS ai_estimated_depth,  -- depth가 length 역할
    JSON_EXTRACT_SCALAR(oi.order_item_product_version_extra, '$.height') AS ai_estimated_height,

    oi.created_at,
    -- 동일 order_id 내 최신 순위
    ROW_NUMBER() OVER (PARTITION BY oi.order_item_order_id ORDER BY oi.created_at DESC) AS rn
  FROM `sazoshop.firestore_snapshot.v2_order_items` oi
  WHERE oi.order_item_order_id IN (SELECT order_item_order_id FROM single_item_orders)
)

-- 최종 학습 데이터셋
SELECT
  -- 식별자
  oid.order_item_order_id,
  oid.order_item_id,
  oid.order_item_product_id,
  oid.order_item_product_version_id,

  -- [INPUT FEATURES] 텍스트 정보
  IFNULL(oid.order_item_title_origin, '') AS product_title_origin,
  IFNULL(oid.order_item_title_target, '') AS product_title_target,
  IFNULL(oid.order_item_product_version_info_category, '') AS product_category,
  IFNULL(oid.order_item_meta_custom_category_name, '') AS custom_category,
  IFNULL(oid.order_item_product_version_site_name, '') AS site_name,
  IFNULL(oid.order_item_product_version_details, '') AS product_details,
  IFNULL(oid.order_item_product_version_info_details, '') AS product_info_details,
  IFNULL(oid.order_item_meta_materials, '') AS materials,
  IFNULL(oid.order_item_meta_clothing_materials, '') AS clothing_materials,
  IFNULL(oid.order_item_meta_hscode, '') AS hscode,

  -- [INPUT FEATURES] 이미지 정보
  IFNULL(oid.thumbnail_urls, '') AS thumbnail_urls,
  IFNULL(oid.thumbnail_count, 0) AS thumbnail_count,

  -- [INPUT FEATURES] 가격 정보
  IFNULL(oid.order_item_price_origin_base, 0) AS price_origin,
  IFNULL(oid.order_item_price_target_base, 0) AS price_krw,

  -- [INPUT FEATURES] URL
  IFNULL(oid.order_item_product_version_url, '') AS product_url,

  -- [LABELS] 실제 측정값
  kse.actual_weight AS actual_weight_kg,
  kse.width_cm AS actual_width_cm,
  kse.length_cm AS actual_length_cm,
  kse.height_cm AS actual_height_cm,
  kse.volume_m3 AS actual_volume_m3,
  kse.volumetric_weight AS volumetric_weight_kg,

  -- [METADATA] 기존 AI 추정값
  oid.ai_estimated_weight_kg,
  oid.ai_estimated_volume_m3,
  SAFE_CAST(oid.ai_estimated_width AS FLOAT64) AS ai_estimated_width_cm,
  SAFE_CAST(oid.ai_estimated_depth AS FLOAT64) AS ai_estimated_length_cm,  -- depth를 length로 매핑
  SAFE_CAST(oid.ai_estimated_height AS FLOAT64) AS ai_estimated_height_cm,
  -- AI 추정 부피 계산 (cm³ -> m³)
  CASE
    WHEN oid.ai_estimated_width IS NOT NULL
     AND oid.ai_estimated_depth IS NOT NULL
     AND oid.ai_estimated_height IS NOT NULL
    THEN SAFE_CAST(oid.ai_estimated_width AS FLOAT64) *
         SAFE_CAST(oid.ai_estimated_depth AS FLOAT64) *
         SAFE_CAST(oid.ai_estimated_height AS FLOAT64) / 1000000
    ELSE NULL
  END AS ai_calculated_volume_m3,

  -- 추정 오차율 계산
  CASE
    WHEN oid.ai_estimated_weight_kg IS NOT NULL AND kse.actual_weight > 0
    THEN ABS(oid.ai_estimated_weight_kg - kse.actual_weight) / kse.actual_weight
    ELSE NULL
  END AS weight_error_rate,

  CASE
    WHEN oid.ai_estimated_volume_m3 IS NOT NULL AND kse.volume_m3 > 0
    THEN ABS(oid.ai_estimated_volume_m3 - kse.volume_m3) / kse.volume_m3
    ELSE NULL
  END AS volume_error_rate,

  -- [METADATA] 기타 정보
  kse.shipping_date,
  oid.created_at AS order_created_at
FROM order_item_details oid
INNER JOIN kse_shipping_data kse ON oid.order_item_order_id = kse.order_id
WHERE
  -- order_id당 최신 아이템만 선택
  oid.rn = 1
  -- 유효한 측정값만
  AND kse.actual_weight > 0
  AND kse.volume_m3 > 0
  -- 비정상적인 값 제외 (예: 100kg 이상, 1m³ 이상)
  AND kse.actual_weight < 100
  AND kse.volume_m3 < 1
  -- 필수 텍스트 정보가 있는 경우만
  AND (oid.order_item_title_origin IS NOT NULL OR oid.order_item_title_target IS NOT NULL)
ORDER BY kse.shipping_date DESC;
