# Keeta UAE — AOR Dashboard

## Data source
`data/AOR_dashboard_final_v2_20260820.xlsx` is an unchanged copy of the approved input workbook. The dashboard embeds its `Consolidated` sheet directly in `index.html`, so it opens without an API or fetch call. Population mappings use `/tmp/files/population.xlsx` at build time only.

## Calculations
- Window: 06–19 Aug 2026; T-1: 19 Aug.
- DoD = 19 Aug vs 18 Aug. WoW = 19 Aug vs 12 Aug. Null/zero denominators render `—`.
- Talabat Order Share, installs, sessions, DAUs, completed orders, S1, A1, AOV and revenue values are carried from the validated Consolidated workbook. AOV is displayed in AED.
- Population contribution = mapped AOR population / sum of all supplied population rows. It is only calculated for direct/cosmetic-normalized supplied mappings.
- Penetration is unavailable because accumulated-user data is absent.

## Daily replacement
1. Place the approved workbook at the path used in `build_aor_dashboard.py` (and update the filename/path if it changes).
2. Place the approved population workbook at `/tmp/files/population.xlsx`.
3. Run `python3 build_aor_dashboard.py` from the workspace. This replaces only `aor-dashboard/index.html` and the copied workbook.
4. Open `index.html` directly or serve `aor-dashboard` with any static server.

## Known data gaps
Sharjah source zones do not genuinely map to the supplied population zones, and Zakher is absent from population data. Al Shahama is not assigned population because the supplied file lists separate Al Shahama 1 and 2 zones only. Penetration must wait for accumulated-user data. The UI lists requested Sharjah areas that were not found in the validated data; no metrics are fabricated.
