#!/usr/bin/env python3
"""Patch real SQL data into existing index.html without changing CSS/layout/fonts.
Strategy: split by aor-section divs, patch each emirate's section independently."""
import re, csv
from collections import defaultdict
from datetime import datetime

INDEX_HTML = "/mnt/openclaw/.openclaw/workspace/aor-dashboard/index.html"
DATA_DIR = "/mnt/openclaw/.openclaw/workspace/aor-dashboard/data"

EMIRATE_MAP = {"Dubai Emirate": "Dubai", "Sharjah Emirate": "Sharjah", "Abu Dhabi  Emirate": "Abu Dhabi"}
AL_AIN_AORS = {"Zakher"}
AOR_NAME_MAP = {
    "Al Khawaneej Al Mizhar": "Al Khawaneej Al Mizhar", "Muhaisnah / Al Mizhar": "Muhaisnah / Al Mizhar",
    "Mirdif": "Mirdif", "Al Warqa": "Al Warqa", "Naad Al Hamar": "Naad Al Hamar",
    "Creek Harbor": "Creek Harbor", "Downtown": "Downtown",
    "Business Bay 1": "Business Bay 1", "Business Bay 2": "Business Bay 2",
    "Barsha South - Arjan": "Barsha South - Arjan", "Arabian Ranches": "Arabian Ranches",
    "Damac Hills / Mudon": "Damac Hills / Mudon", "Muwaileh Commercial": "Muwaileh",
    "Al Badee Suburb Siyouh Suburb": "Siyouh", "Al Rehmania Suburb": "Al Rehmania",
    "Al Saadah": "Al Saadah", "Khalifa city": "Khalifa City", "Shakhbout City": "Shakhbout City",
    "Al Shamkhah": "Al Shamkhah", "Bani Yas": "Bani Yas", "Al Shahama": "Al Shahama",
    "Yas Island": "Yas Island", "AI Falah": "Al Falah", "Zakher": "Zakher",
}

def read_csv(name):
    with open(f"{DATA_DIR}/{name}") as f:
        return list(csv.DictReader(f))

def pi(v):
    try: return int(float(v)) if v else 0
    except: return 0

def norm_em(aor, em):
    if aor.strip() in AL_AIN_AORS: return "Al Ain"
    return EMIRATE_MAP.get(em, em)

def norm_aor(s):
    return AOR_NAME_MAP.get(s.strip(), s.strip())

def fmt(v):
    if v is None or v == 0: return "\u2014"
    return f"{v:,}"

def dod(s):
    if len(s) < 2 or s[-2] == 0: return None
    return ((s[-1] - s[-2]) / s[-2]) * 100

def wow(s):
    if len(s) < 7: return None
    t7 = s[-8] if len(s) >= 8 else s[0]
    if t7 == 0: return None
    return ((s[-1] - t7) / t7) * 100

def fs(v):
    if v is None: return "\u2014"
    return f"+{v:.1f}%" if v >= 0 else f"{v:.1f}%"

def sc(v):
    if v is None: return "dod-na"
    return "dod-pos" if v >= 0 else "dod-neg"

# Load data
q1 = read_csv("query1_orders_dau.csv")
q2 = read_csv("query2_sessions.csv")
q3 = read_csv("query3_s1_a1.csv")
q4 = read_csv("query4_emirate_totals.csv")

merged = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
for row in q1:
    em = norm_em(row['aor_name'], row['emirate'])
    aor = norm_aor(row['aor_name'])
    merged[em][aor][row['dt']]['dau'] = pi(row['dau'])
    merged[em][aor][row['dt']]['orders'] = pi(row['completed_orders'])
for row in q2:
    em = norm_em(row['aor_name'], row['emirate'])
    aor = norm_aor(row['aor_name'])
    merged[em][aor][row['dt']]['sessions'] = pi(row['sessions'])
    merged[em][aor][row['dt']]['installs'] = pi(row['first_visit_devices'])
for row in q3:
    em = norm_em(row['aor_name'], row['emirate'])
    aor = norm_aor(row['aor_name'])
    merged[em][aor][row['dt']]['s1Orders'] = pi(row['s1_orders'])
    merged[em][aor][row['dt']]['a1Orders'] = pi(row['a1_orders'])

em_totals = defaultdict(lambda: defaultdict(int))
for row in q4:
    em = norm_em("", row['emirate'])
    if em in ["Dubai", "Sharjah", "Abu Dhabi", "Al Ain"]:
        em_totals[em][row['dt']] = pi(row['total_completed_orders'])

all_dates = sorted(set(dt for em in merged.values() for aor in em.values() for dt in aor.keys()))
last_dt = all_dates[-1]
print(f"Dates: {all_dates}, last: {last_dt}")

# For S1/A1 which may not have the latest date, use the latest available date
q3_dates = sorted(set(row['dt'] for row in q3))
last_q3_dt = q3_dates[-1] if q3_dates else last_dt
print(f"S1/A1 last date: {last_q3_dt}")

# Compute emirate KPIs
emirate_kpis = {}
for em in ["Dubai", "Sharjah", "Abu Dhabi", "Al Ain"]:
    em_data = merged.get(em, {})
    daily = {m: [] for m in ['orders','sessions','dau','installs']}
    for dt in all_dates:
        for m in daily:
            daily[m].append(sum(d.get(dt, {}).get(m, 0) for d in em_data.values()))
    
    total_orders = daily['orders'][-1] if daily['orders'] else 0
    total_sessions = daily['sessions'][-1] if daily['sessions'] else 0
    total_daus = daily['dau'][-1] if daily['dau'] else 0
    total_installs = daily['installs'][-1] if daily['installs'] else 0
    avg_daus = round(sum(daily['dau']) / max(len(all_dates), 1))
    
    if em == "Al Ain":
        all_em_orders = em_totals["Abu Dhabi"].get(last_dt, 0)
    else:
        all_em_orders = em_totals[em].get(last_dt, 0)
    em_share = (total_orders / all_em_orders * 100) if all_em_orders > 0 else 0
    
    emirate_kpis[em] = {
        'Daily Orders': (total_orders, dod(daily['orders'])),
        'Total Sessions': (total_sessions, dod(daily['sessions'])),
        'Avg DAUs': (avg_daus, dod(daily['dau'])),
        'Total DAUs': (avg_daus, dod(daily['dau'])),
        'Total Installs': (total_installs, dod(daily['installs'])),
        'emirateShare': em_share,
    }
    print(f"  {em}: tracked={total_orders:,} / all={all_em_orders:,} -> share={em_share:.1f}%")

# Load HTML
with open(INDEX_HTML) as f:
    html = f.read()

# Split HTML by aor-section divs
# Find each aor-section div: <div class="aor-section" id="aor-N">...</div>
# We need to find the boundaries between sections

section_starts = [(m.start(), m.end()) for m in re.finditer(r'<div class="aor-section" id="aor-\d+">', html)]
print(f"\nFound {len(section_starts)} aor-sections")

# Also find the end of each section (start of next section or end of body)
# The sections are consecutive in the body
parts = []
for i, (s_start, s_end) in enumerate(section_starts):
    # Section content goes from s_end to next section start or end of container
    next_start = section_starts[i+1][0] if i+1 < len(section_starts) else html.find('</body>')
    # But we need the closing </div> for the section itself
    # Actually, let's find the section content between the opening tag and the next opening or end
    section_content_end = next_start
    # Walk backwards to find closing div tags
    # Actually, let's just take everything between this opening and the next opening
    section_html = html[s_start:section_content_end]
    
    # Extract emirate name from h2
    h2_match = re.search(r'<h2[^>]*>([^<]+)</h2>', section_html)
    if h2_match:
        em_name = h2_match.group(1).strip()
        print(f"  Section {i}: {em_name}")
        parts.append((s_start, section_content_end, em_name, section_html))

# Now patch each section
new_html = html
offset = 0  # Track offset changes from replacements

for start, end, em_name, section_html in parts:
    em = em_name
    kpi = emirate_kpis.get(em)
    if not kpi:
        continue
    
    patched = section_html
    
    # 1. Patch KPI cards in this section
    # Pattern: kpi-value">VALUE</div><div class="kpi-label">LABEL</div><span class="kpi-dod CLS">DoD: SHIFT</span>[emirate span]</div>
    kpi_re = re.compile(
        r'(<div class="kpi-card"><div class="kpi-value">)([0-9,.%\u2014]+)(</div><div class="kpi-label">)'
        r'(Daily Orders|Total Sessions|Avg DAUs|Total DAUs|Total Installs|Avg AOV|Talabat %)'
        r'(</div><span class="kpi-dod )([^"]*?)(\">DoD: )([^<]*)(</span>)'
        r'(<span class="kpi-dod dod-na\">Emirate: [^<]*</span>)?'
        r'(</div>)'
    )
    
    def replace_kpi(match):
        label = match.group(4)
        kpi_data = kpi.get(label)
        if not kpi_data:
            return match.group(0)  # Keep original for AOV/Talabat
        
        val, dod_val = kpi_data
        new_val = fmt(val)
        new_dod = fs(dod_val)
        new_cls = sc(dod_val)
        
        em_share_span = ""
        if label == "Daily Orders":
            es = kpi['emirateShare']
            em_share_span = f'<span class="kpi-dod dod-na">Emirate: {es:.1f}%</span>'
        
        return (f'{match.group(1)}{new_val}{match.group(3)}{label}'
                f'{match.group(5)}{new_cls}{match.group(7)}{new_dod}{match.group(9)}'
                f'{em_share_span}{match.group(11) if match.group(11) else ""}'
                f'{match.group(12) if match.lastindex >= 12 else ""}')
    
    # Actually, let me count groups properly
    # Group 1: <div class="kpi-card"><div class="kpi-value">
    # Group 2: VALUE
    # Group 3: </div><div class="kpi-label">
    # Group 4: LABEL
    # Group 5: </div><span class="kpi-dod 
    # Group 6: CLS
    # Group 7: ">DoD: 
    # Group 8: SHIFT
    # Group 9: </span>
    # Group 10: <span class="kpi-dod dod-na">Emirate: X.X%</span> (optional)
    # Group 11: </div>
    
    def replace_kpi2(match):
        label = match.group(4)
        kpi_data = kpi.get(label)
        if not kpi_data:
            return match.group(0)
        
        val, dod_val = kpi_data
        new_val = fmt(val)
        new_dod = fs(dod_val)
        new_cls = sc(dod_val)
        
        em_share_span = ""
        if label == "Daily Orders":
            es = kpi['emirateShare']
            em_share_span = f'<span class="kpi-dod dod-na">Emirate: {es:.1f}%</span>'
        
        return (f'{match.group(1)}{new_val}{match.group(3)}{label}'
                f'{match.group(5)}{new_cls}{match.group(7)}{new_dod}{match.group(9)}'
                f'{em_share_span}'
                f'{match.group(11)}')
    
    patched = kpi_re.sub(replace_kpi2, patched)
    
    # 2. Patch sub-card metric values in this section
    sub_card_pattern = re.compile(
        r'(sub-card-header" style="color:[^"]*">)([^<]+)(</div>.*?)(?=sub-card-header|</div></div></div></div>|$)',
        re.DOTALL
    )
    
    sub_cards = list(sub_card_pattern.finditer(patched))
    for card in sub_cards:
        aor_name = card.group(2).strip()
        aor_data = None
        for em_key in ["Dubai", "Sharjah", "Abu Dhabi", "Al Ain"]:
            if aor_name in merged.get(em_key, {}):
                aor_data = merged[em_key][aor_name]
                break
        if not aor_data:
            continue
        
        latest = aor_data.get(last_dt, {})
        latest_s1a1 = aor_data.get(last_q3_dt, {})
        orders = latest.get('orders', 0)
        a1 = latest_s1a1.get('a1Orders', 0)
        talabat_pct = (a1 / orders * 100) if orders > 0 else 0
        
        metric_vals = [
            ("Talabat %", f"{talabat_pct:.1f}%" if orders > 0 else "\u2014"),
            ("Installs", fmt(latest.get('installs', 0))),
            ("Sessions", fmt(latest.get('sessions', 0))),
            ("DAUs", fmt(latest.get('dau', 0))),
            ("Daily Orders", fmt(latest.get('orders', 0))),
            ("S1 Orders", fmt(latest_s1a1.get('s1Orders', 0))),
            ("A1 Orders", fmt(latest_s1a1.get('a1Orders', 0))),
            ("AOV (AED)", "\u2014"),
        ]
        
        card_html = card.group(0)
        patched_card = card_html
        for label, new_val in metric_vals:
            mpat = re.compile(
                r'(metric-label">' + re.escape(label) + r'</div><div class="metric-actual ">)([0-9,.%\u2014]+|—)(</div>)'
            )
            patched_card = mpat.sub(lambda m: f"{m.group(1)}{new_val}{m.group(3)}", patched_card, count=1)
        
        patched = patched[:card.start()] + patched_card + patched[card.end():]
    
    # 3. Patch data table rows
    table_pattern = re.compile(r'<tr><td[^>]*>([^<]+)</td>(.*?)</tr>', re.DOTALL)
    table_rows = list(table_pattern.finditer(patched))
    for row in table_rows:
        aor_name = row.group(1).strip()
        cells = row.group(2)
        if aor_name in ('Sub-area', 'GRAND TOTAL', 'Total', ''):
            continue
        aor_data = None
        for em_key in ["Dubai", "Sharjah", "Abu Dhabi", "Al Ain"]:
            if aor_name in merged.get(em_key, {}):
                aor_data = merged[em_key][aor_name]
                break
        if not aor_data:
            continue
        latest = aor_data.get(last_dt, {})
        latest_s1a1 = aor_data.get(last_q3_dt, {})
        orders = latest.get('orders', 0)
        a1 = latest_s1a1.get('a1Orders', 0)
        talabat_pct = (a1 / orders * 100) if orders > 0 else 0
        new_vals = [
            f"{talabat_pct:.1f}%" if orders > 0 else "\u2014",
            fmt(latest.get('installs', 0)),
            fmt(latest.get('sessions', 0)),
            fmt(latest.get('dau', 0)),
            fmt(latest.get('orders', 0)),
            fmt(latest_s1a1.get('s1Orders', 0)),
            fmt(latest_s1a1.get('a1Orders', 0)),
            "\u2014",
        ]
        cell_pattern = re.compile(r'<td>([^<]*)</td>')
        cell_matches = list(cell_pattern.finditer(cells))
        for i, cm in enumerate(cell_matches):
            if i < len(new_vals):
                cells = cells[:cm.start()] + f'<td>{new_vals[i]}</td>' + cells[cm.end():]
        patched = patched[:row.start()] + f'<tr><td>{aor_name}</td>{cells}</tr>' + patched[row.end():]
    
    # Replace section in html
    new_html = new_html[:start + offset] + patched + new_html[end + offset:]
    offset += len(patched) - (end - start)

# Update date range
start_dt = datetime.strptime(all_dates[0], "%Y%m%d")
end_dt = datetime.strptime(all_dates[-1], "%Y%m%d")
month_map = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
date_range = f"{month_map[start_dt.month]} {start_dt.day} \u2013 {month_map[end_dt.month]} {end_dt.day}, 2026"

new_html = re.sub(r'[A-Z][a-z]{2} \d{1,2}\s*\u2013\s*[A-Z][a-z]{2} \d{1,2}, 2026', date_range, new_html)
new_html = re.sub(r'(Last Updated:\s*)[0-9]{4}-[0-9]{2}-[0-9]{2}', f'Last Updated: {end_dt.strftime("%Y-%m-%d")}', new_html)
# Also update the kpi-section-label date
new_html = re.sub(r'Previous Day Metrics \(Aug \d+\)', f'Previous Day Metrics ({month_map[end_dt.month]} {end_dt.day})', new_html)

with open(INDEX_HTML, 'w') as f:
    f.write(new_html)

print(f"\nDone! Size: {len(new_html):,} bytes")
print(f"Date range: {date_range}")
