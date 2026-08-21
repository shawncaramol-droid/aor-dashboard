SELECT
    f.dt,
    f.today_visit_most_aor_id AS aor_id,
    COALESCE(d.aor_name, 'Unknown') AS aor_name,
    COALESCE(d.org_2_name, 'Unknown') AS emirate,
    COUNT(DISTINCT f.user_id) AS dau,
    COUNT(DISTINCT CASE WHEN f.user_layers_3_id = 1 THEN f.user_id END) AS new_users,
    SUM(CASE WHEN f.finish_order_id IS NOT NULL THEN 1 ELSE 0 END) AS completed_orders,
    COUNT(DISTINCT CASE WHEN f.is_fst_ord = '1' THEN f.finish_user_id END) AS first_order_users
FROM mart_sailor_global.topic_flow_user_txn_conversion_funnel_d f
LEFT JOIN (
    SELECT DISTINCT aor_id, aor_name, org_2_name 
    FROM mart_sailor_global.dim_sailor_aor_org_flat 
    WHERE region = 'AE'
) d ON CAST(f.today_visit_most_aor_id AS int) = d.aor_id
WHERE f.dt BETWEEN '20260814' AND '20260820'
  AND f.region = 'AE'
  AND f.today_visit_most_aor_id IN (
    '500000419', '500000414', '500000444', '500000443', '510040002', '500000386',
    '500000367', '500000424', '500000450', '500000362', '500000404', '510260000',
    '300000634', '500001013', '500001044',
    '500000590', '510130002', '500000609', '500000611', '500000610', '500000603',
    '500000602', '510040004', '500001022'
  )
GROUP BY f.dt, f.today_visit_most_aor_id, d.aor_name, d.org_2_name
ORDER BY f.dt, emirate, aor_name
