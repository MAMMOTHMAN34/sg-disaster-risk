"""Who is exposed: residents living in the sea-level-rise flood zones.

This is the "so what" of the coastal analysis. For each planning area I take the
share of its land that floods under each sea-level scenario and multiply by its
resident population to estimate how many people are exposed, then set the island
total against the government's S$100 billion coastal-defence commitment.

ASSUMPTIONS / LIMITS:
  * Residents are assumed to be spread evenly across an area's land, so exposure scales
    with flooded land share. In reality, housing may sit on higher ground, so this
    is a rough first-order estimate.
  * "Resident" population (Census 2020) = citizens + PRs only. It excludes the
    ~1.5m non-resident workers, so daytime exposure in workplaces (e.g. Tuas)
    is undercounted.
  * Uses today's population against future sea levels.
  
    python -m src.features.economic_exposure

Output:
    data/processed/economic_exposure_by_area.csv
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
POPULATION = REPO_ROOT / "data" / "raw" / "population" / "population_by_area.csv"
SCENARIOS = REPO_ROOT / "data" / "processed" / "slr_scenarios_by_area.csv"
OUT_PATH = REPO_ROOT / "data" / "processed" / "economic_exposure_by_area.csv"

COASTAL_DEFENCE_SGD = 100_000_000_000  # S$100 billion commitment (2019)

# scenario column in the SLR file -> friendly label
SCENARIO_PCT = {
    "pct_y2100_1m": ("exposed_2100_1m", "+1 m (≈2100)"),
    "pct_y2150_2m": ("exposed_2150_2m", "+2 m (≈2150)"),
    "pct_worstcase_4m": ("exposed_worst_4m", "+4 m (worst case)"),
}


def build_exposure() -> pd.DataFrame:
    pop = pd.read_csv(POPULATION)
    slr = pd.read_csv(SCENARIOS)

    df = slr.merge(pop, on="planning_area", how="left")
    df["population"] = df["population"].fillna(0).astype(int)

    for pct_col, (out_col, _label) in SCENARIO_PCT.items():
        df[out_col] = (df["population"] * df[pct_col] / 100).round().astype(int)

    keep = ["planning_area", "population", "land_area_km2", "pct_y2150_2m",
            *[c for c, _ in SCENARIO_PCT.values()]]
    return df[keep].sort_values("exposed_2150_2m", ascending=False).reset_index(drop=True)


def report(df: pd.DataFrame) -> None:
    total_pop = df["population"].sum()
    print(f"Total resident population (Census 2020): {total_pop:,}\n")
    print("Residents exposed by sea-level scenario:")
    for pct_col, (out_col, label) in SCENARIO_PCT.items():
        exposed = int(df[out_col].sum())
        share = exposed / total_pop * 100
        cost = COASTAL_DEFENCE_SGD / exposed if exposed else float("nan")
        print(f"  {label:<18} {exposed:>9,} residents ({share:4.1f}% of pop)  "
              f"→ S${cost:,.0f} of coastal-defence budget per exposed resident")

    print("\nMost-affected residential areas at +2 m (≈2150):")
    cols = ["planning_area", "population", "pct_y2150_2m", "exposed_2150_2m"]
    print(df[df["exposed_2150_2m"] > 0][cols].head(10).to_string(index=False))


def main() -> None:
    df = build_exposure()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    report(df)
    print(f"\nSaved to {OUT_PATH}")


if __name__ == "__main__":
    main()
