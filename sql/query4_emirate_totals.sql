-- Total daily orders per emirate across ALL AORs (not just tracked ones)
-- Used to calculate emirate share: tracked AOR orders / total emirate orders
SELECT
    f.dt,
    COALESCE(d.org_2_name, 'Unknown') AS emirate,
    COUNT(DISTINCT f.user_id) AS total_dau,
    SUM(CASE WHEN f.finish_order_id IS NOT NULL THEN 1 ELSE 0 END) AS total_completed_orders,
    COUNT(DISTINCT CASE WHEN f.is_fst_ord = '1' THEN f.finish_user_id END) AS total_new_users
FROM mart_sailor_global.topic_flow_user_txn_conversion_funnel_d f
LEFT JOIN (
    SELECT DISTINCT aor_id, aor_name, org_2_name 
    FROM mart_sailor_global.dim_sailor_aor_org_flat 
    WHERE region = 'AE'
) d ON CAST(f.today_visit_most_aor_id AS int) = d.aor_id
WHERE f.dt BETWEEN '20260814' AND '20260820'
  AND f.region = 'AE'
GROUP BY f.dt, d.org_2_name
ORDER BY f.dt, emirate
