"""Render the static maps embedded in the README.

Produces two planning-area choropleths from the processed layers:
  - coastal sea-level-rise exposure (% land flooded at +2m)
  - residents exposed at +2m

    python -m src.viz.figures

Outputs:
    reports/figures/coastal_slr_2m.png
    reports/figures/residents_exposed_2m.png
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
BOUNDARIES = REPO_ROOT / "data" / "raw" / "boundaries" / "planning_areas.geojson"
SLR = REPO_ROOT / "data" / "processed" / "slr_scenarios_by_area.geojson"
EXPOSURE = REPO_ROOT / "data" / "processed" / "economic_exposure_by_area.csv"
FIG_DIR = REPO_ROOT / "reports" / "figures"


def choropleth(gdf: gpd.GeoDataFrame, column: str, title: str, label: str,
               cmap: str, out_name: str) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
    gdf.plot(column=column, cmap=cmap, linewidth=0.3, edgecolor="white",
             legend=True, legend_kwds={"label": label, "shrink": 0.7},
             missing_kwds={"color": "lightgrey", "label": "no data"}, ax=ax)
    ax.set_title(title, fontsize=12)
    ax.axis("off")
    fig.tight_layout()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / out_name, dpi=130, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    slr = gpd.read_file(SLR)
    choropleth(
        slr, "pct_y2150_2m",
        "Coastal flood exposure at +2 m sea-level rise (≈2150)",
        "% of land ≤ 2 m", "Blues", "coastal_slr_2m.png",
    )

    boundaries = gpd.read_file(BOUNDARIES).assign(
        planning_area=lambda g: g["PLN_AREA_N"].str.title()
    )
    exposure = pd.read_csv(EXPOSURE)
    gdf = boundaries.merge(exposure, on="planning_area", how="left")
    choropleth(
        gdf, "exposed_2150_2m",
        "Residents exposed at +2 m sea-level rise (≈2150)",
        "residents in flood zone", "OrRd", "residents_exposed_2m.png",
    )
    print(f"Saved figures to {FIG_DIR}")


if __name__ == "__main__":
    main()
