"""
Build the static JSON payload for the Food Systems Emissions dashboard.

Reproduces the cleaning in Scripts/emissions_dashboard.py exactly (2010+, clean items,
valid ISO3, positive emissions, complete-source years only), then writes compact
index-encoded JSON that the browser aggregates on the fly.

    conda activate foodtwin_dataset
    python preprocess/build_data.py          # ~3-5 min, reads ~900 MB of CSV

Writes to ../data/ (relative to this file).
"""

import json
import re
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pycountry

BASE = Path("/Users/kushankbajaj/Library/CloudStorage/OneDriveFileProvider-FoodandAgricultureOrganization/Consumption_based_emissions/Output")
PROD_SRC  = BASE / "crop_country_year_emissions_by_source.csv"
CONS_SRC  = BASE / "consumption_country_year_emissions_by_source.csv"
BILATERAL = BASE / "bilateral_sankey_precomputed.parquet"
OUT = Path(__file__).resolve().parent.parent / "data"

# ── Constants copied from Scripts/emissions_dashboard.py ──────────────────────
YEAR_MIN = 2010
BAD_ITEM_PATTERNS = ["unknown", "residual", "aggregate", "unmapped"]
BAD_COUNTRY_CODES = {"ZZZ", "XKX"}
ISO3_RE = re.compile(r"^[A-Z]{3}$")

SOURCE_GAS = {
    "Synthetic fertilizers": "N2O", "Crop residues": "N2O", "Burning-crop residues": "CH4 / N2O",
    "Rice cultivation": "CH4", "Enteric fermentation": "CH4", "Manure management": "CH4 / N2O",
    "Manure applied to soils": "N2O", "Manure left on pasture": "N2O",
    "Land-use: Net forest conversion": "CO2", "Land-use: Fire emissions": "CO2 / CH4 / N2O",
    "Land-use: Drainage cropland": "CO2 / N2O", "Land-use: Drainage grassland": "CO2 / N2O",
    "Fertilizer manufacturing": "CO2", "Pesticide manufacturing": "CO2", "Energy use": "CO2",
    "Processing": "CO2", "Packaging": "CO2", "Food transport": "CO2", "Retail": "CO2",
    "Cold chain F-gas": "F-gases", "Household consumption": "CO2 / CH4", "Solid food waste": "CH4",
    "Incineration": "CO2", "Industrial wastewater": "CH4", "Domestic wastewater": "CH4",
    "Agrifood systems waste": "CH4",
}

COMMODITY_GROUPS = {
    "Cereals":        ["wheat","rice","maize","barley","oat","rye","sorghum","millet","triticale","grain"],
    "Pulses":         ["lentil","chickpea","bean","pea","pigeon","faba","broad","soybean","pulse"],
    "Oilseeds & Oils":["rapeseed","sunflower","palm","coconut","groundnut","sesame","cottonseed","olive","canola"],
    "Beef & Buffalo": ["beef","buffalo","bovine","cattle"],
    "Poultry":        ["poultry","chicken","duck","turkey","broiler"],
    "Other Meat":     ["pig","pork","sheep","goat","horse","rabbit","swine"],
    "Dairy & Eggs":   ["milk","egg","butter","cheese","yoghurt","cream","dairy"],
    "Fruits":         ["apple","banana","citrus","grape","mango","pineapple","watermelon","avocado","strawberry","fruit"],
    "Vegetables":     ["tomato","potato","onion","cabbage","carrot","pepper","cucumber","lettuce","vegetable"],
    "Sugar":          ["sugar","cane","beet"],
}


def is_valid_iso3(code):
    return isinstance(code, str) and bool(ISO3_RE.match(code)) and code not in BAD_COUNTRY_CODES


def is_clean_item(item):
    if not isinstance(item, str): return False
    il = item.lower()
    return not any(tok in il for tok in BAD_ITEM_PATTERNS)


def get_group(item):
    s = item.lower()
    for grp, kws in COMMODITY_GROUPS.items():
        if any(k in s for k in kws): return grp
    return "Other"


def sig(x, n=5):
    """Round to n significant figures for compact JSON."""
    x = float(x)
    if x == 0 or not np.isfinite(x): return 0
    return float(f"{x:.{n}g}")


def dump(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, separators=(",", ":"))


# ── Load & clean ──────────────────────────────────────────────────────────────
print("Loading production (by source)...")
prod = pd.read_csv(PROD_SRC, low_memory=False, dtype={"ISO3": str},
                   usecols=["ISO3", "Year", "Item", "Emission_Source", "Emission_kgCO2e", "Production_t"])
prod["Year"] = pd.to_numeric(prod["Year"], errors="coerce")
prod["Emission_kgCO2e"] = pd.to_numeric(prod["Emission_kgCO2e"], errors="coerce")
prod["Production_t"] = pd.to_numeric(prod["Production_t"], errors="coerce")
prod = prod[(prod["Year"] >= YEAR_MIN) & prod["Item"].map(is_clean_item)
            & prod["ISO3"].map(is_valid_iso3) & (prod["Emission_kgCO2e"] > 0)].copy()

print("Loading consumption (by source)...")
cons = pd.read_csv(CONS_SRC, low_memory=False, dtype={"Consumer_ISO3": str},
                   usecols=["Consumer_ISO3", "Year", "Item", "Emission_Source", "Embodied_Emission_kgCO2e"])
cons["Year"] = pd.to_numeric(cons["Year"], errors="coerce")
cons["Embodied_Emission_kgCO2e"] = pd.to_numeric(cons["Embodied_Emission_kgCO2e"], errors="coerce")
cons = cons[(cons["Year"] >= YEAR_MIN) & cons["Item"].map(is_clean_item)
            & cons["Consumer_ISO3"].map(is_valid_iso3) & (cons["Embodied_Emission_kgCO2e"] > 0)].copy()

print("Loading bilateral...")
trade = pd.read_parquet(BILATERAL)

# Complete-source years only (drops partial years such as 2024)
n_src = prod["Emission_Source"].nunique()
per_year = prod.groupby("Year")["Emission_Source"].nunique()
complete = sorted(int(y) for y in per_year[per_year == n_src].index)
YEAR_MAX = max(complete)
years = list(range(YEAR_MIN, YEAR_MAX + 1))
prod = prod[prod["Year"].astype(int).isin(complete)]
cons = cons[cons["Year"].between(YEAR_MIN, YEAR_MAX)]
trade = trade[trade["Year"].between(YEAR_MIN, YEAR_MAX)]
print(f"Window {YEAR_MIN}-{YEAR_MAX}; complete years {complete}")

# ── Indices ───────────────────────────────────────────────────────────────────
sources = sorted(prod["Emission_Source"].unique())
items = sorted(set(prod["Item"]) | set(cons["Item"]) | set(trade["Item"].dropna()))
groups = list(COMMODITY_GROUPS) + ["Other"]
iso_names = {c.alpha_3: c.name for c in pycountry.countries}
countries = sorted(set(prod["ISO3"]) | set(cons["Consumer_ISO3"])
                   | set(trade["Producer_ISO3"].dropna()) | set(trade["Consumer_ISO3"].dropna()))
s_ix = {s: i for i, s in enumerate(sources)}
i_ix = {s: i for i, s in enumerate(items)}
g_ix = {s: i for i, s in enumerate(groups)}
c_ix = {s: i for i, s in enumerate(countries)}

for df in (prod, cons):
    df["y"] = df["Year"].astype(int) - YEAR_MIN
    df["i"] = df["Item"].map(i_ix)
    df["s"] = df["Emission_Source"].map(s_ix)
    df["g"] = df["Item"].map(lambda it: g_ix[get_group(it)])
prod["kt"] = prod["Emission_kgCO2e"] / 1e6
cons["kt"] = cons["Embodied_Emission_kgCO2e"] / 1e6

# ── Per-country production cubes: [year, item, source, kt] + production tonnes ──
def write_prod(df, key):
    em = df.groupby(["y", "i", "s"], as_index=False)["kt"].sum()
    pt = (df.dropna(subset=["Production_t"])
            .drop_duplicates(subset=["ISO3", "y", "i"])
            .groupby(["y", "i"], as_index=False)["Production_t"].sum())
    dump({"em": [[int(a), int(b), int(c), sig(v)] for a, b, c, v in em.itertuples(index=False)],
          "pt": [[int(a), int(b), sig(v)] for a, b, v in pt.itertuples(index=False)]},
         OUT / "prod" / f"{key}.json")

print("Writing production cubes...")
write_prod(prod, "GLOBAL")
prod_countries = sorted(prod["ISO3"].unique())
for iso, d in prod.groupby("ISO3"):
    write_prod(d, iso)

# ── Shift cube: country x year x group x source, production vs consumption ────
print("Writing shift cube...")
def cube(df, iso_col):
    a = df.groupby([iso_col, "y", "g", "s"], as_index=False)["kt"].sum()
    return [[c_ix[c], int(y), int(g), int(s), sig(v, 4)] for c, y, g, s, v in a.itertuples(index=False)]
dump({"prod": cube(prod, "ISO3"), "cons": cube(cons, "Consumer_ISO3")}, OUT / "shift.json")

# ── Bilateral flows: [producer, consumer, item, year, kt] ─────────────────────
print("Writing trade flows...")
t = trade.dropna(subset=["Producer_ISO3", "Consumer_ISO3", "Item", "Embodied_Mt"])
t = t[t["Embodied_Mt"] > 0]
dump([[c_ix[p], c_ix[c], i_ix[it], int(y) - YEAR_MIN, sig(v * 1000, 4)]
      for p, c, it, y, v in t[["Producer_ISO3", "Consumer_ISO3", "Item", "Year", "Embodied_Mt"]].itertuples(index=False)],
     OUT / "trade.json")

# ── Meta ──────────────────────────────────────────────────────────────────────
src_mtime = date.fromtimestamp(PROD_SRC.stat().st_mtime).isoformat()
dump({
    "yearMin": YEAR_MIN, "yearMax": YEAR_MAX, "years": years,
    "sources": [{"name": s, "gas": SOURCE_GAS.get(s, "CO2")} for s in sources],
    "items": [{"name": it, "g": g_ix[get_group(it)]} for it in items],
    "groups": groups,
    "countries": [{"iso": c, "name": iso_names.get(c, c)} for c in countries],
    "prodCountries": prod_countries,
    "tradeConsumers": sorted(t["Consumer_ISO3"].unique()),
    "dataVintage": src_mtime,
    "built": date.today().isoformat(),
    "checkGlobalMtPerYr": round(prod["kt"].sum() / len(years) / 1e3, 1),
}, OUT / "meta.json")

print(f"Global annual-avg production: {prod['kt'].sum() / len(years) / 1e3:.1f} Mt CO2e")
print("Done ->", OUT)
