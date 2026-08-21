#!/usr/bin/env python3
"""Patch real SQL data into existing index.html without breaking HTML structure.
Strategy: Use targeted regex on the full HTML string, no section slicing."""
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
q3_dates = sorted(set(row['dt'] for row in q3))
last_q3_dt = q3_dates[-1] if q3_dates else last_dt
print(f"Dates: {all_dates}, last: {last_dt}, S1/A1 last: {last_q3_dt}")

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

orig_size = len(html)
print(f"\nOriginal HTML size: {orig_size:,} bytes")

# Strategy: Find each KPI card by its label and replace value+DoD in-place
# KPI card pattern (greedy to capture full card):
# <div class="kpi-card"><div class="kpi-value">VALUE</div><div class="kpi-label">LABEL</div><span class="kpi-dod CLASS">DoD: SHIFT</span>[<span class="kpi-dod dod-na">Emirate: X.X%</span>]</div>

kpi_pattern = re.compile(
    r'(<div class="kpi-card"><div class="kpi-value">)([0-9,.%\u2014]+)'
    r'(</div><div class="kpi-label">)(Daily Orders|Total Sessions|Avg DAUs|Total DAUs|Total Installs|Avg AOV|Talabat %)'
    r'(</div><span class="kpi-dod )([^"]+)(\">DoD: )([^<]*)(</span>)'
    r'(<span class="kpi-dod dod-na\">Emirate: [^<]*</span>)?'
    r'(</div>)'
)

def replace_kpi(match):
    prefix1 = match.group(1)
    old_val = match.group(2)
    prefix2 = match.group(3)
    label = match.group(4)
    prefix3 = match.group(5)
    old_cls = match.group(6)
    prefix4 = match.group(7)
    old_shift = match.group(8)
    suffix1 = match.group(9)
    emirate_span = match.group(10)
    suffix2 = match.group(11)
    
    kpi_data = emirate_kpis.get(label_to_emirate(label, html, match.start()))
    if not kpi_data:
        return match.group(0)  # Keep original for AOV/Talabat
    
    val, dod_val = kpi_data[label]
    new_val = fmt(val)
    new_dod = fs(dod_val)
    new_cls = sc(dod_val)
    
    em_share_span = emirate_span or ""
    if label == "Daily Orders":
        em = label_to_emirate(label, html, match.start())
        if em and 'emirateShare' in emirate_kpis.get(em, {}):
            es = emirate_kpis[em]['emirateShare']
            em_share_span = f'<span class="kpi-dod dod-na">Emirate: {es:.1f}%</span>'
    
    return f'{prefix1}{new_val}{prefix2}{label}{prefix3}{new_cls}{prefix4}{new_dod}{suffix1}{em_share_span}{suffix2}'

# Map KPI label to emirate by finding which section the match is in
def label_to_emirate(label, html, pos):
    """Find which emirate section this position belongs to."""
    # Find the last aor-section opening before this position
    sections = list(re.finditer(r'<div class="aor-section" id="aor-(\d+)">', html))
    emirates_by_idx = ["Dubai", "Sharjah", "Abu Dhabi", "Al Ain"]
    
    current_em = None
    for i, m in enumerate(sections):
        if m.start() <= pos:
            idx = int(m.group(1))
            if idx < len(emirates_by_idx):
                current_em = emirates_by_idx[idx]
    
    # Also check h2 in the section to confirm
    if current_em is None:
        # Find nearest h2 before position
        h2s = list(re.finditer(r'<h2[^>]*>([^<]+)</h2>', html[:pos]))
        if h2s:
            current_em = h2s[-1].group(1).strip()
    
    return current_em

# Actually, let me do it differently - process per section
# Find all KPI cards and determine their emirate by position
sections = list(re.finditer(r'<div class="aor-section" id="aor-(\d+)">', html))
emirates_by_idx = ["Dubai", "Sharjah", "Abu Dhabi", "Al Ain"]

section_ranges = []
for i, m in enumerate(sections):
    start = m.start()
    end = sections[i+1].start() if i+1 < len(sections) else html.find('</body>')
    idx = int(m.group(1))
    em = emirates_by_idx[idx] if idx < len(emirates_by_idx) else None
    section_ranges.append((start, end, em))
    print(f"  Section {idx} ({em}): {start}-{end}")

# Patch KPI cards per section
new_html = html
for s_start, s_end, em in section_ranges:
    if not em:
        continue
    kpi = emirate_kpis.get(em)
    if not kpi:
        continue
    
    section = new_html[s_start:s_end]
    
    def replace_kpi_in_section(match):
        label = match.group(4)
        kpi_tuple = kpi.get(label)
        if not kpi_tuple:
            return match.group(0)
        
        val, dod_val = kpi_tuple
        new_val = fmt(val)
        new_dod = fs(dod_val)
        new_cls = sc(dod_val)
        
        em_share_span = match.group(10) or ""
        if label == "Daily Orders":
            es = kpi['emirateShare']
            em_share_span = f'<span class="kpi-dod dod-na">Emirate: {es:.1f}%</span>'
        
        return (f'{match.group(1)}{new_val}{match.group(3)}{label}'
                f'{match.group(5)}{new_cls}{match.group(7)}{new_dod}{match.group(9)}'
                f'{em_share_span}{match.group(11)}')
    
    kpi_re = re.compile(
        r'(<div class="kpi-card"><div class="kpi-value">)([0-9,.%\u2014]+)'
        r'(</div><div class="kpi-label">)(Daily Orders|Total Sessions|Avg DAUs|Total DAUs|Total Installs|Avg AOV|Talabat %)'
        r'(</div><span class="kpi-dod )([^"]+)(\">DoD: )([^<]*)(</span>)'
        r'(<span class="kpi-dod dod-na\">Emirate: [^<]*</span>)?'
        r'(</div>)'
    )
    
    patched_section = kpi_re.sub(replace_kpi_in_section, section)
    new_html = new_html[:s_start] + patched_section + new_html[s_end:]

print(f"\nAfter KPI patch: {len(new_html):,} bytes (delta: {len(new_html)-orig_size})")

# Patch sub-card metrics
# Pattern: sub-card-header" style="color:...">AOR_NAME</div>
# followed by metric rows: metric-label">LABEL</div><div class="metric-actual ">VALUE</div>
sub_card_re = re.compile(
    r'(sub-card-header" style="color:[^"]*">)([^<]+)(</div>)(.*?)(?=sub-card-header" style|</div>\s*</div>\s*</div>\s*<div class="chart-section"|\Z)',
    re.DOTALL
)

def patch_sub_cards(html_str):
    def replacer(match):
        aor_name = match.group(2).strip()
        # Find this AOR's data
        aor_data = None
        for em_key in ["Dubai", "Sharjah", "Abu Dhabi", "Al Ain"]:
            if aor_name in merged.get(em_key, {}):
                aor_data = merged[em_key][aor_name]
                break
        if not aor_data:
            return match.group(0)
        
        latest = aor_data.get(last_dt, {})
        latest_s1a1 = aor_data.get(last_q3_dt, {})
        orders = latest.get('orders', 0)
        a1 = latest_s1a1.get('a1Orders', 0)
        talabat_pct = (a1 / orders * 100) if orders > 0 else 0
        
        metric_vals = {
            "Talabat %": f"{talabat_pct:.1f}%" if orders > 0 else "\u2014",
            "Installs": fmt(latest.get('installs', 0)),
            "Sessions": fmt(latest.get('sessions', 0)),
            "DAUs": fmt(latest.get('dau', 0)),
            "Daily Orders": fmt(latest.get('orders', 0)),
            "S1 Orders": fmt(latest_s1a1.get('s1Orders', 0)),
            "A1 Orders": fmt(latest_s1a1.get('a1Orders', 0)),
            "AOV (AED)": "\u2014",
        }
        
        card_content = match.group(4)
        for label, new_val in metric_vals.items():
            mpat = re.compile(
                r'(metric-label">' + re.escape(label) + r'</div><div class="metric-actual )(">)'
                r'([0-9,.%\u2014]+|—)'
            )
            card_content = mpat.sub(lambda m: f'{m.group(1)}{m.group(2)}{new_val}', card_content, count=1)
        
        return match.group(1) + match.group(2) + match.group(3) + card_content
    
    return sub_card_re.sub(replacer, html_str)

new_html = patch_sub_cards(new_html)
print(f"After sub-card patch: {len(new_html):,} bytes")

# Patch table rows
# Pattern: <tr><td class="left">AOR_NAME</td><td>VAL</td>...</tr>
table_row_re = re.compile(
    r'(<tr><td[^>]*>)([^<]+)(</td>)(.*?)(</tr>)',
    re.DOTALL
)

def patch_table_rows(html_str):
    def replacer(match):
        aor_name = match.group(2).strip()
        if aor_name in ('Sub-area', 'GRAND TOTAL', 'Total', ''):
            return match.group(0)
        
        aor_data = None
        for em_key in ["Dubai", "Sharjah", "Abu Dhabi", "Al Ain"]:
            if aor_name in merged.get(em_key, {}):
                aor_data = merged[em_key][aor_name]
                break
        if not aor_data:
            return match.group(0)
        
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
        
        cells = match.group(4)
        cell_re = re.compile(r'<td>([^<]*)</td>')
        cell_matches = list(cell_re.finditer(cells))
        for i, cm in enumerate(cell_matches):
            if i < len(new_vals):
                cells = cells[:cm.start()] + f'<td>{new_vals[i]}</td>' + cells[cm.end():]
        
        return match.group(1) + match.group(2) + match.group(3) + cells + match.group(5)
    
    return table_row_re.sub(replacer, html_str)

new_html = patch_table_rows(new_html)
print(f"After table patch: {len(new_html):,} bytes")

# Update date range
start_dt = datetime.strptime(all_dates[0], "%Y%m%d")
end_dt = datetime.strptime(all_dates[-1], "%Y%m%d")
month_map = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
date_range = f"{month_map[start_dt.month]} {start_dt.day} \u2013 {month_map[end_dt.month]} {end_dt.day}, 2026"

new_html = re.sub(r'[A-Z][a-z]{2} \d{1,2}\s*\u2013\s*[A-Z][a-z]{2} \d{1,2}, 2026', date_range, new_html)
new_html = re.sub(r'(Last Updated:\s*)[0-9]{4}-[0-9]{2}-[0-9]{2}', f'Last Updated: {end_dt.strftime("%Y-%m-%d")}', new_html)
new_html = re.sub(r'Previous Day Metrics \(Aug \d+\)', f'Previous Day Metrics ({month_map[end_dt.month]} {end_dt.day})', new_html)

# Verify div balance
opens = new_html.count('<div')
closes = new_html.count('</div>')
print(f"\nFinal div balance: {opens} opens, {closes} closes, diff={opens-closes}")

with open(INDEX_HTML, 'w') as f:
    f.write(new_html)

print(f"\nDone! Size: {len(new_html):,} bytes (was {orig_size:,})")
print(f"Date range: {date_range}")
