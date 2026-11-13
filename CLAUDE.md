# CLAUDE.md

Static dashboard of agrifood emissions by source (production-based plus trade shift). No build step.

## Files

| Path | What it is |
|---|---|
| `index.html` | The whole app: CSS, controls, and the JS that aggregates JSON rows and draws Plotly charts |
| `preprocess/build_data.py` | Reads the large pipeline outputs in `../Output/`, applies the cleaning from `../Scripts/emissions_dashboard.py`, writes `data/` |
| `data/meta.json` | Lookup arrays (years, sources+gas, items+group, countries) and vintage/build dates |
| `data/prod/{ISO3}.json`, `GLOBAL.json` | `em`: `[yearIdx, itemIdx, sourceIdx, kt]`; `pt`: `[yearIdx, itemIdx, tonnes]` |
| `data/shift.json` | `prod`/`cons`: `[countryIdx, yearIdx, groupIdx, sourceIdx, kt]` |
| `data/trade.json` | `[producerIdx, consumerIdx, itemIdx, yearIdx, kt]` |
| `.github/workflows/deploy.yml` | Publishes repo root to GitHub Pages on push to `main` |

## Conventions

- Every value in `data/` is in kt CO₂e (production in tonnes). The JS divides by 1000 to get Mt, and
  by the number of years in the range to get the annual average.
- Commodity group is decided at build time (`get_group`) and stored as `items[i].g`. Change it there,
  not in JS.
- Colours (`SOURCE_COLORS`, `GAS_COLORS`, `GROUP_COLORS`) are copied from the Dash app; keep them in sync.
- Fetch paths are relative (`data/...`). Keep them relative, or the site breaks under `/food-systems-emissions/`.

## Rebuild and check

`conda activate foodtwin_dataset && python preprocess/build_data.py`, then serve the parent directory
and confirm the KPI tile matches the "Global annual-avg production" line the build prints.

The data is **preliminary** (vintage 2026-04-30). Update the banner in `index.html` when the corrected
by-source tables are regenerated.
