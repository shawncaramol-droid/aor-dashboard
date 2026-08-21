#!/usr/bin/env python3
"""
Build the AOR Dashboard HTML with real data from SQL queries.
Reads CSV outputs, merges data, computes metrics, and injects into the template.
"""

import csv
import json
import os
from collections import defaultdict
from datetime import datetime

BASE_DIR = "/mnt/openclaw/.openclaw/workspace/aor-dashboard"
DATA_DIR = os.path.join(BASE_DIR, "data")
TEMPLATE_PATH = "/mnt/openclaw/.openclaw/workspace/aor_dashboard.html"
OUTPUT_PATH = os.path.join(BASE_DIR, "index.html")

# AOR name mapping: SQL AOR name -> Dashboard sub-area name
AOR_NAME_MAP = {
    "Al Khawaneej Al Mizhar": "Al Khawaneej Al Mizhar",
    "Muhaisnah / Al Mizhar": "Muhaisnah / Al Mizhar",
    "Mirdif": "Mirdiff",
    "Al Warqa": "Al Warqa",
    "Naad Al Hamar": "Naad Al Hamar",
    "Creek Harbor": "Creek Harbor",
    "Downtown": "Downtown",
    "Business Bay 1": "Business Bay 1 & 2",
    "Business Bay 2": "Business Bay 1 & 2",
    "Barsha South - Arjan": "Barsha South - Arjan",
    "Arabian Ranches": "Arabian Ranches",
    "Damac Hills / Mudon": "Damac Hills / Mudon",
    "Muwaileh Commercial": "Muwaileh",
    "Al Badee Suburb Siyouh Suburb": "Around University City",
    "Al Rehmania Suburb": "Al Rehmania",
    "Al Saadah": "Al Saadah",
    "Khalifa city": "Khalifa City",
    "Shakhbout City": "Shakhbout City",
    "Al Shamkhah": "Al Shamkhah",
    "Bani Yas": "Bani Yas",
    "Al Shahama": "Al Shahama",
    "Yas Island": "Yas Island",
    "AI Falah": "Al Falah",
    "Zakher": "Zakher",
}

EMIRATE_MAP = {
    "Dubai Emirate": "Dubai",
    "Sharjah Emirate": "Sharjah",
    "Abu Dhabi  Emirate": "Abu Dhabi",
}

# AORs that belong to Al Ain despite being tagged as Abu Dhabi Emirate in source data
AL_AIN_AORS = {"Zakher"}

AOR_SUBAREAS = {
    "Dubai": ["Al Khawaneej Al Mizhar","Muhaisnah / Al Mizhar","Mirdiff","Al Warqa","Naad Al Hamar","Creek Harbor","Downtown","Business Bay 1 & 2","Barsha South - Arjan","Arabian Ranches","Damac Hills / Mudon"],
    "Sharjah": ["Muwaileh","Around University City","Al Rehmania","Al Rahmania","Siyouh","Al Sajaa","Al Jlail","Hay Hoshi","Hay Al Badee","Al Sehma","Al Riaquibah"],
    "Abu Dhabi": ["Al Saadah","Khalifa City","Shakhbout City","Al Shamkhah","Bani Yas","Al Shahama","Yas Island","Al Falah"],
    "Al Ain": ["Zakher"],
}

POPULATION_MAP = {
    "Dubai": {"Al Khawaneej Al Mizhar":45078,"Muhaisnah / Al Mizhar":53352,"Mirdiff":74135,"Al Warqa":74865,"Naad Al Hamar":28189,"Creek Harbor":21958,"Downtown":29922,"Business Bay 1 & 2":16177,"Barsha South - Arjan":60761,"Arabian Ranches":42149,"Damac Hills / Mudon":34197},
    "Abu Dhabi": {"Al Saadah":80000,"Khalifa City":104930,"Shakhbout City":33540,"Al Shamkhah":107615,"Bani Yas":120000,"Al Shahama":30500,"Yas Island":40000,"Al Falah":82000},
    "Sharjah": {},
    "Al Ain": {},
}

AOR_THEMES = {"Dubai":"blue","Sharjah":"green","Abu Dhabi":"orange","Al Ain":"purple"}

METRIC_DEFS = [
    {"key":"talabatOrderShare","label":"Talabat %","format":"pct","decimals":1},
    {"key":"installs","label":"Installs","format":"int","decimals":0},
    {"key":"sessions","label":"Sessions","format":"int","decimals":0},
    {"key":"daus","label":"DAUs","format":"int","decimals":0},
    {"key":"orders","label":"Daily Orders","format":"int","decimals":0},
    {"key":"s1Orders","label":"S1 Orders","format":"int","decimals":0},
    {"key":"a1Orders","label":"A1 Orders","format":"int","decimals":0},
    {"key":"aov","label":"AOV (AED)","format":"currency","decimals":2},
]


def read_csv(path):
    with open(path, 'r') as f:
        return list(csv.DictReader(f))


def normalize_emirate(aor_name, emirate_str):
    """Map source emirate to dashboard emirate, handling Al Ain special case."""
    if aor_name.strip() in AL_AIN_AORS:
        return "Al Ain"
    return EMIRATE_MAP.get(emirate_str, emirate_str)


def normalize_aor(s):
    s = s.strip()
    return AOR_NAME_MAP.get(s, s)


def parse_int(val):
    if not val:
        return 0
    try:
        return int(float(val))
    except:
        return 0


def compute_metric_series(daily_values):
    if not daily_values:
        return {"values": [], "t1Value": None, "dodShift": None, "wowShift": None, "sparkline": []}
    sorted_dates = sorted(daily_values.keys())
    values = [{"date": d, "value": daily_values[d]} for d in sorted_dates]
    t1 = values[-1]["value"]
    t2 = values[-2]["value"] if len(values) >= 2 else None
    t7 = values[-7]["value"] if len(values) >= 7 else None
    dod = ((t1 - t2) / t2 * 100) if (t2 is not None and t2 != 0) else None
    wow = ((t1 - t7) / t7 * 100) if (t7 is not None and t7 != 0) else None
    return {"values": values, "t1Value": t1, "dodShift": dod, "wowShift": wow, "sparkline": [v["value"] for v in values[-7:]]}


def empty_metric():
    return {"values": [], "t1Value": None, "dodShift": None, "wowShift": None, "sparkline": []}


def build_dashboard_data():
    q1 = read_csv(os.path.join(DATA_DIR, "query1_orders_dau.csv"))
    q2 = read_csv(os.path.join(DATA_DIR, "query2_sessions.csv"))
    q3 = read_csv(os.path.join(DATA_DIR, "query3_s1_a1.csv"))

    # merged[emirate][aor_name][dt] = {metric: value}
    merged = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))

    for row in q1:
        dt = row['dt']
        em = normalize_emirate(row["aor_name"], row["emirate"])
        aor = normalize_aor(row['aor_name'])
        merged[em][aor][dt]['dau'] = parse_int(row['dau'])
        merged[em][aor][dt]['orders'] = parse_int(row['completed_orders'])
        merged[em][aor][dt]['first_order_users'] = parse_int(row['first_order_users'])

    for row in q2:
        dt = row['dt']
        em = normalize_emirate(row["aor_name"], row["emirate"])
        aor = normalize_aor(row['aor_name'])
        merged[em][aor][dt]['sessions'] = parse_int(row['sessions'])
        merged[em][aor][dt]['installs'] = parse_int(row['first_visit_devices'])

    for row in q3:
        dt = row['dt']
        em = normalize_emirate(row["aor_name"], row["emirate"])
        aor = normalize_aor(row['aor_name'])
        merged[em][aor][dt]['s1Orders'] = parse_int(row['s1_orders'])
        merged[em][aor][dt]['a1Orders'] = parse_int(row['a1_orders'])

    # Merge Business Bay 1 & 2
    for em, aors in list(merged.items()):
        if "Business Bay 1" in aors and "Business Bay 2" in aors:
            bb1, bb2 = aors["Business Bay 1"], aors["Business Bay 2"]
            all_dts = sorted(set(list(bb1.keys()) + list(bb2.keys())))
            merged_bb = {}
            for dt in all_dts:
                merged_bb[dt] = {}
                for metric in ['dau','orders','first_order_users','sessions','installs','s1Orders','a1Orders']:
                    merged_bb[dt][metric] = bb1.get(dt, {}).get(metric, 0) + bb2.get(dt, {}).get(metric, 0)
            del aors["Business Bay 1"]
            del aors["Business Bay 2"]
            aors["Business Bay 1 & 2"] = merged_bb

    # Get all dates
    all_dates = set()
    for em, aors in merged.items():
        for aor, dt_data in aors.items():
            all_dates.update(dt_data.keys())
    all_dates = sorted(all_dates)

    if not all_dates:
        print("ERROR: No dates found!")
        return None

    # Format date range
    start_dt = datetime.strptime(all_dates[0], "%Y%m%d")
    end_dt = datetime.strptime(all_dates[-1], "%Y%m%d")
    month_map = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
    date_window = f"{month_map[start_dt.month]} {start_dt.day} – {month_map[end_dt.month]} {end_dt.day}, 2026"
    last_updated = end_dt.strftime("%Y-%m-%d")

    # UAE total orders by date
    uae_totals = defaultdict(int)
    emirate_totals = defaultdict(lambda: defaultdict(int))
    for em, aors in merged.items():
        for aor, dt_data in aors.items():
            for dt, m in dt_data.items():
                uae_totals[dt] += m.get('orders', 0)
                emirate_totals[em][dt] += m.get('orders', 0)

    # Build dashboard data
    data = {"lastUpdated": last_updated, "dateWindow": date_window, "aors": {}}

    for emirate in ["Dubai", "Sharjah", "Abu Dhabi", "Al Ain"]:
        data["aors"][emirate] = {"subAreas": {}}
        for sa_name in AOR_SUBAREAS.get(emirate, []):
            pop = POPULATION_MAP.get(emirate, {}).get(sa_name)
            aor_data = merged.get(emirate, {}).get(sa_name, {})

            if not aor_data:
                data["aors"][emirate]["subAreas"][sa_name] = {
                    "population": pop,
                    "metrics": {m["key"]: empty_metric() for m in METRIC_DEFS}
                }
                continue

            daily = {dt: m for dt, m in aor_data.items()}
            metrics = {}
            metrics["orders"] = compute_metric_series({dt: m.get('orders',0) for dt,m in daily.items()})
            metrics["daus"] = compute_metric_series({dt: m.get('dau',0) for dt,m in daily.items()})
            metrics["sessions"] = compute_metric_series({dt: m.get('sessions',0) for dt,m in daily.items()})
            metrics["installs"] = compute_metric_series({dt: m.get('installs',0) for dt,m in daily.items()})
            metrics["s1Orders"] = compute_metric_series({dt: m.get('s1Orders',0) for dt,m in daily.items()})
            metrics["a1Orders"] = compute_metric_series({dt: m.get('a1Orders',0) for dt,m in daily.items()})
            # Talabat % proxy: A1 orders / total orders
            talabat_daily = {}
            for dt, m in daily.items():
                total = m.get('orders', 0)
                talabat_daily[dt] = m.get('a1Orders', 0) / total if total > 0 else 0
            metrics["talabatOrderShare"] = compute_metric_series(talabat_daily)
            metrics["aov"] = empty_metric()

            data["aors"][emirate]["subAreas"][sa_name] = {
                "population": pop,
                "metrics": metrics
            }

    # Compute KPI ribbon data per emirate
    kpi = {}
    last_date = all_dates[-1]
    for emirate in ["Dubai", "Sharjah", "Abu Dhabi", "Al Ain"]:
        sub = data["aors"][emirate]["subAreas"]
        total_orders = sum(s["metrics"]["orders"]["t1Value"] or 0 for s in sub.values())
        total_sessions = sum(s["metrics"]["sessions"]["t1Value"] or 0 for s in sub.values())
        total_daus = sum(s["metrics"]["daus"]["t1Value"] or 0 for s in sub.values())
        total_installs = sum(s["metrics"]["installs"]["t1Value"] or 0 for s in sub.values())
        uae_total = uae_totals.get(last_date, 0)
        em_total = emirate_totals.get(emirate, {}).get(last_date, 0)
        share = (em_total / uae_total * 100) if uae_total > 0 else 0
        kpi[emirate] = {
            "dailyOrders": total_orders,
            "totalSessions": total_sessions,
            "avgDaus": round(total_daus / max(len(all_dates), 1)),
            "totalInstalls": total_installs,
            "emirateShare": round(share, 1)
        }

    return data, kpi


def generate_html(data, kpi):
    with open(TEMPLATE_PATH, 'r') as f:
        template = f.read()

    # We'll take the template, keep all CSS and HTML structure,
    # but replace the JS data section with real data.

    # The template structure:
    # 1. HTML/CSS (head + body start + dashboard-header + aorContainer div)
    # 2. <script src="chart.js">
    # 3. <script> with:
    #    a. METRIC_DEFS, POPULATION_MAP, AOR_THEMES, AOR_SUBAREAS config
    #    b. genSampleData() + buildSampleData() — REPLACE
    #    c. enrichOrdersPct() — KEEP
    #    d. const DASHBOARD_DATA = ... — REPLACE with real data
    #    e. All rendering functions — KEEP
    #    f. renderDashboard() / init — KEEP

    # Find the section markers
    config_start = template.find('const METRIC_DEFS=')
    sample_data_start = template.find('// ═══════════════════════════════════════════════════════════════\n// SAMPLE DATA GENERATOR')
    enrich_start = template.find('function enrichOrdersPct(')
    dashboard_data_start = template.find('const DASHBOARD_DATA=')
    render_start = template.find('// ═══════════════════════════════════════════════════════════════\n// RENDERING')

    # Extract parts we want to keep
    before_config = template[:config_start]  # HTML + CSS + chart.js script tag start

    # Config section (METRIC_DEFS through start of sample data)
    config_section = template[config_start:sample_data_start]

    # enrichOrdersPct function (keep as-is)
    enrich_section = template[enrich_start:dashboard_data_start]

    # Rendering section (everything from RENDERING to end)
    render_section = template[render_start:]

    # Build the JS data injection
    data_json = json.dumps(data, default=str)

    # Build KPI ribbon HTML
    def fmt_int(v):
        return f"{v:,}" if v else "—"
    def fmt_pct(v):
        return f"{v:.1f}%" if v is not None else "—"

    # We need to add KPI ribbon to the renderDashboard function
    # Instead of modifying the template's renderDashboard, we'll inject KPI data
    # into DASHBOARD_DATA and modify the render function to include KPI ribbons

    # Actually, let's keep it simpler: inject the data as DASHBOARD_DATA,
    # and add a kpiData object. The template's renderDashboard will render sub-areas
    # and tables. We'll prepend KPI ribbon HTML to each aor-card-body.

    # Build the complete JS section
    kpi_json = json.dumps(kpi, default=str)

    js_section = f'''
{config_section}
// ═══════════════════════════════════════════════════════════════
// REAL DATA — Populated from SQL queries
// ═══════════════════════════════════════════════════════════════

{enrich_section}
const DASHBOARD_DATA = enrichOrdersPct({data_json});
const KPI_DATA = {kpi_json};

{render_section}'''

    # Modify renderDashboard to add KPI ribbon
    # We need to insert KPI ribbon HTML before the subarea-summary-grid in each aor-body
    # Let's patch the renderDashboard function

    full_html = before_config + js_section

    # Now patch: add KPI ribbon rendering
    # Find the renderDashboard function and inject KPI ribbon code
    old_kpi_line = "    const subCount=Object.keys(aorData.subAreas).length;"
    new_kpi_code = """    const subCount=Object.keys(aorData.subAreas).length;
    const kpi=KPI_DATA[aorName]||{};
    const fmtI=(v)=>v?v.toLocaleString('en-US'):'—';
    const fmtP=(v)=>(v!==null&&v!==undefined)?v.toFixed(1)+'%':'—';
    const kpiRibbon='<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin-bottom:20px;padding:16px;background:var(--bg-secondary);border-radius:10px;border:1px solid var(--border-color)">'+
      '<div style="text-align:center"><div style="font-size:.7rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.05em">Daily Orders</div><div style="font-size:1.4rem;font-weight:700;color:var(--text-primary)">'+fmtI(kpi.dailyOrders)+'</div><div style="font-size:.72rem;color:var(--text-muted)" class="dod-na">Emirate: '+fmtP(kpi.emirateShare)+'</div></div>'+
      '<div style="text-align:center"><div style="font-size:.7rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.05em">Total Sessions</div><div style="font-size:1.4rem;font-weight:700;color:var(--text-primary)">'+fmtI(kpi.totalSessions)+'</div></div>'+
      '<div style="text-align:center"><div style="font-size:.7rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.05em">Avg DAUs</div><div style="font-size:1.4rem;font-weight:700;color:var(--text-primary)">'+fmtI(kpi.avgDaus)+'</div></div>'+
      '<div style="text-align:center"><div style="font-size:.7rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.05em">Total Installs</div><div style="font-size:1.4rem;font-weight:700;color:var(--text-primary)">'+fmtI(kpi.totalInstalls)+'</div></div>'+
      '<div style="text-align:center"><div style="font-size:.7rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.05em">Avg AOV</div><div style="font-size:1.4rem;font-weight:700;color:var(--text-muted)">—</div></div>'+
      '<div style="text-align:center"><div style="font-size:.7rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.05em">Talabat %</div><div style="font-size:1.4rem;font-weight:700;color:var(--text-muted)">—</div></div>'+
      '</div>';"""

    full_html = full_html.replace(old_kpi_line, new_kpi_code)

    # Inject KPI ribbon into the aor-body HTML
    old_body_start = "'<div class=\"aor-body\" id=\"aorBody_'+aid+'\">'+\n        '<div class=\"subarea-summary-grid\">'+summaryHtml+'</div>'+"
    new_body_start = "'<div class=\"aor-body\" id=\"aorBody_'+aid+'\">'+\n        kpiRibbon+\n        '<div class=\"subarea-summary-grid\">'+summaryHtml+'</div>'+"

    full_html = full_html.replace(old_body_start, new_body_start)

    # Also update the header description from "14-day rolling window" to "7-day rolling window"
    full_html = full_html.replace("14-day rolling window", "7-day rolling window")

    return full_html


def main():
    print("Building dashboard data from CSV files...")
    result = build_dashboard_data()
    if result is None:
        print("ERROR: Failed to build dashboard data")
        return

    data, kpi = result
    print(f"Data built: {len(data['aors'])} emirates")
    for em, sub in data['aors'].items():
        print(f"  {em}: {len(sub['subAreas'])} sub-areas")

    print(f"Date window: {data['dateWindow']}")
    print(f"Last updated: {data['lastUpdated']}")

    print("\nGenerating HTML...")
    html = generate_html(data, kpi)

    print(f"Writing to {OUTPUT_PATH}...")
    with open(OUTPUT_PATH, 'w') as f:
        f.write(html)

    print(f"Done! File size: {len(html):,} bytes")
    print(f"KPI data: {json.dumps(kpi, indent=2)}")


if __name__ == "__main__":
    main()
