# Food Systems Emissions

A static, single-file dashboard (vanilla JS and Plotly.js, no build step) showing agrifood
greenhouse-gas emissions across all 26 sources: on-farm, land-use change, pre/post-production
and waste. It covers 199 producing countries and 2010–2023. Most views are production-based;
the trade views compare production with consumption and follow embodied emissions through
international trade. Deployed at <https://kushankbajaj.com/food-systems-emissions/>.

> **Preliminary.** The data is from pipeline outputs dated 2026-04-30, before the land-use
> re-run, the July livestock residual fixes and the September Kastner commodity-mapping fixes.
> The page carries a banner saying so. Do not cite these numbers.

This is a static port of the Dash app `Scripts/emissions_dashboard.py`. It keeps the same filters,
thresholds and charts but no longer needs a Python server.

## What it shows

- **Overview.** Which sources drive emissions and how that changed over time. It has a stacked
  area chart by source, a donut of the source mix, and a single-year Sankey from source to gas to
  commodity group. Land-use (net forest conversion) and enteric fermentation are the two largest
  sources globally, at about 16% each.
- **Food Groups.** Which commodities emit the most, and which are the most emission-intensive per
  kg. Two charts: the top 20 commodities by annual-average Mt CO₂e, stacked by source, and the
  top 20 by kg CO₂e per kg produced. Cattle meat comes top on both.
- **Trade & Shift.** Who exports embodied emissions and who imports them. The net-shift chart
  shows production minus consumption by country; Brazil is the largest net exporter and China
  the largest net importer. The bilateral Sankey runs producer → commodity → consumer and is
  dominated by Brazilian soy going to China.

The shared controls are year range, country, food group and emission source; the KPI tile shows
annual-average production emissions for that selection. Changing a filter re-aggregates
in the browser. The only network requests are the first load of a country's file (about 50–800 KB)
and of the trade files, which load once when the Trade tab is first opened.

## Time coverage

2010–2023. 2010 is the first year in which pre/post-production sources are allocated; before
that they are zero, which would make earlier years look artificially low. The build keeps only
years in which all 26 sources are present. That drops 2024, which is partial.

All values are **annual averages over the selected range**: the total divided by the number of
years in the range.

## Method

| Key | Shown as | Definition |
|---|---|---|
| `prod/*.json` `em` | Production emissions | `Emission_kgCO2e` from `crop_country_year_emissions_by_source.csv`, attributed to the producing country |
| `prod/*.json` `pt` | Production (t) | `Production_t`, deduplicated per country–year–item (it repeats across sources in the source table) |
| `shift.json` `cons` | Consumption emissions | `Embodied_Emission_kgCO2e` from `consumption_country_year_emissions_by_source.csv`, attributed to the consuming country |
| `trade.json` | Embodied flow | `Embodied_Mt` from `bilateral_sankey_precomputed.parquet` (international trade only) |
| Intensity | kg CO₂e / kg food | Σ emissions ÷ Σ production over the window; items below 1,000 t are excluded |
| Shift | Production − consumption | Countries above 0.5 Mt/yr on either side that appear in both tables |

GWP100 values are IPCC AR5 (CH₄ = 25, N₂O = 298). Commodity groups come from keyword matching
on the item name (`COMMODITY_GROUPS` in `preprocess/build_data.py`). These are point estimates;
the source tables have no uncertainty band.

## Data pipeline

```
Output/crop_country_year_emissions_by_source.csv          (321 MB)  ┐
Output/consumption_country_year_emissions_by_source.csv   (604 MB)  ├─ preprocess/build_data.py ─► data/meta.json
Output/bilateral_sankey_precomputed.parquet               (1.6 MB)  ┘                             data/prod/{ISO3|GLOBAL}.json
                                                                                                   data/shift.json
                                                                                                   data/trade.json
```

```bash
conda activate foodtwin_dataset
python preprocess/build_data.py     # ~3–5 min; overwrites data/
```

Rows in the JSON files are encoded as indices into the `meta.json` arrays: `[year − yearMin, item, source, kt]`.
The build prints the global annual average, 17,438.7 Mt CO₂e for 2010–2023, which should match the
KPI tile when the page loads.

## Development

```bash
cd ..  &&  python3 -m http.server 8765
# open http://localhost:8765/food-systems-emissions/
```

Deployment is automatic: pushing to `main` triggers `.github/workflows/deploy.yml`, which publishes
the repo root to GitHub Pages. All fetches use relative paths, so the site works under any base path.

## Known limitations

- **Food groups are wrong (also stated in the page banner) for about 16% of emissions.** Keyword matching is checked in order, so
  "Raw milk of cattle" matches *cattle* and lands in Beef & Buffalo (12% of the global total), as does
  buffalo milk (2.4%). "Raw milk of goats" matches *oat* and lands in Cereals. Pears and peaches match
  *pea* and land in Pulses. Eggplants match *egg* and land in Dairy & Eggs. Soya beans (8.6%) and cocoa
  beans fall under Pulses. Dairy & Eggs therefore contains little beyond hen eggs. This bug is inherited
  from the Dash app.
- **Stale inputs** (see the banner). Land-use attribution has not run end to end since April. The livestock
  residual fixes and the Kastner mapping fixes are not reflected.
- **Food transport is on a different basis** from the other 25 sources. It is a bottom-up bilateral estimate
  of about 175% of the FAOSTAT figure; the others are top-down and FAO-normalised.
- **Land-use change uses FAOSTAT**, which gives about 4 Gt CO₂/yr, roughly twice the DeDuCE spatial estimate.
  Fire is allocated to crops by area share, including wildfire.
- The country filter lists producing countries only, so countries that only consume are absent from it. The
  net-shift chart drops countries missing from either table.
- When a single source is selected, the intensity chart still divides by total production of each item, not
  only production on rows that carry that source. This differs slightly from the Dash app and is the more
  consistent denominator.
- Opening the Trade tab downloads about 5.6 MB (gzipped) of shift and flow data.
- The nine Pacific SIDS excluded from the transport publication figures are still included here. Their effect
  on totals is under 0.03%.

## Sources

FAOSTAT emissions domains (GWP AR5); Kastner et al. trade-adjusted production; bilateral transport model
(FAO Consumption_based_emissions project). Data vintage 2026-04-30.
