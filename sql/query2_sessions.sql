SELECT
    s.dt,
    s.aor_id,
    COALESCE(d.aor_name, 'Unknown') AS aor_name,
    COALESCE(d.org_2_name, 'Unknown') AS emirate,
    COUNT(DISTINCT s.session_id) AS sessions,
    COUNT(DISTINCT CASE WHEN s.is_fst_visit = 1 THEN s.session_id END) AS first_visit_sessions,
    COUNT(DISTINCT CASE WHEN s.is_fst_visit = 1 THEN s.uuid END) AS first_visit_devices
FROM mart_sailor_global.aggr_flow_uuid_dau_attribution_d s
LEFT JOIN (
    SELECT DISTINCT aor_id, aor_name, org_2_name 
    FROM mart_sailor_global.dim_sailor_aor_org_flat 
    WHERE region = 'AE'
) d ON s.aor_id = d.aor_id
WHERE s.dt BETWEEN '20260814' AND '20260820'
  AND s.region = 'AE'
  AND s.is_dau = 1
  AND s.aor_id IN (
    500000419, 500000414, 500000444, 500000443, 510040002, 500000386,
    500000367, 500000424, 500000450, 500000362, 500000404, 510260000,
    300000634, 500001013, 500001044,
    500000590, 510130002, 500000609, 500000611, 500000610, 500000603,
    500000602, 510040004, 500001022
  )
GROUP BY s.dt, s.aor_id, d.aor_name, d.org_2_name
ORDER BY s.dt, emirate, aor_name
