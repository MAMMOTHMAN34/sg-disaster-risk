"""Build the sea-level-rise inundation layer: low-lying land per planning area.

This is the first real *result* of the project. I take the raw SRTM elevation
grid and the 55 planning-area polygons and:

  1. Spatial-join each grid point to the planning area that contains it. Points
     that fall over sea match no polygon and are dropped. This is the "clip to
     land" step that fixes the misleading raw "% below 1 m" (which was inflated
     by ocean points read as ~0 m).
  2. For each planning area, compute the share of its land sampled below the
     official sea-level-rise thresholds (1m, 2m, 5m).

As the grid is regular, each point stands for roughly equal ground area, so
"share of points below X" is a fair proxy for "share of land area below X".

    python -m src.features.inundation

Outputs:
    data/processed/inundation_by_area.csv      one row per planning area
    data/processed/inundation_by_area.geojson  same, joined to polygons (for maps)
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
ELEVATION_CSV = REPO_ROOT / "data" / "raw" / "elevation" / "elevation_grid.csv"
BOUNDARIES = REPO_ROOT / "data" / "raw" / "boundaries" / "planning_areas.geojson"
OUT_DIR = REPO_ROOT / "data" / "processed"

WGS84 = 4326   # lon/lat, what both inputs use
SVY21 = 3414   # Singapore national grid, metres — for area in km2
SLR_THRESHOLDS_M = (1, 2, 5)


def load_points() -> gpd.GeoDataFrame:
    """Read the elevation grid CSV into a GeoDataFrame of points."""
    df = pd.read_csv(ELEVATION_CSV)
    return gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
        crs=WGS84,
    )


def clip_points_to_areas(points: gpd.GeoDataFrame, areas: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Tag each elevation point with its planning area; drop points over sea."""
    areas = areas[["PLN_AREA_N", "REGION_N", "geometry"]].rename(
        columns={"PLN_AREA_N": "planning_area", "REGION_N": "region"}
    )
    joined = gpd.sjoin(points, areas, how="inner", predicate="within")
    joined["planning_area"] = joined["planning_area"].str.title()
    joined["region"] = joined["region"].str.title()
    return joined


def aggregate_by_area(points_on_land: gpd.GeoDataFrame, areas: gpd.GeoDataFrame) -> pd.DataFrame:
    """One row per planning area: low-lying shares + land area."""
    # Land area per planning area, in km2 (reproject to metres first).
    area_km2 = (
        areas.to_crs(SVY21)
        .assign(land_area_km2=lambda g: g.geometry.area / 1e6)
        .assign(planning_area=lambda g: g["PLN_AREA_N"].str.title())
        [["planning_area", "land_area_km2"]]
    )

    grouped = points_on_land.groupby(["planning_area", "region"])["elevation_m"]
    rows = []
    for (area, region), elev in grouped:
        row = {
            "planning_area": area,
            "region": region,
            "n_land_points": len(elev),
            "elev_min_m": round(elev.min(), 1),
            "elev_median_m": round(elev.median(), 1),
        }
        for t in SLR_THRESHOLDS_M:
            row[f"pct_below_{t}m"] = round((elev <= t).mean() * 100, 1)
        rows.append(row)

    out = pd.DataFrame(rows).merge(area_km2, on="planning_area", how="left")
    return out.sort_values("pct_below_2m", ascending=False).reset_index(drop=True)


def report(by_area: pd.DataFrame, points_on_land: gpd.GeoDataFrame) -> None:
    """Print the headline: real low-lying numbers, now that sea is removed."""
    elev = points_on_land["elevation_m"]
    print(f"\nLand points (sea removed): {len(points_on_land)}")
    for t in SLR_THRESHOLDS_M:
        print(f"  Real share of land <= {t} m: {(elev <= t).mean() * 100:.1f}%")

    print("\nMost low-lying planning areas (by % of land <= 2 m):")
    cols = ["planning_area", "region", "pct_below_1m", "pct_below_2m", "pct_below_5m", "n_land_points"]
    top = by_area[cols].head(10)
    print(top.to_string(index=False))


def main() -> None:
    points = load_points()
    areas = gpd.read_file(BOUNDARIES)

    points_on_land = clip_points_to_areas(points, areas)
    by_area = aggregate_by_area(points_on_land, areas)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    by_area.to_csv(OUT_DIR / "inundation_by_area.csv", index=False)

    # Join stats back onto polygons so the dashboard can colour the map directly.
    geo = areas.assign(planning_area=areas["PLN_AREA_N"].str.title()).merge(
        by_area.drop(columns="region"), on="planning_area", how="left"
    )
    geo.to_file(OUT_DIR / "inundation_by_area.geojson", driver="GeoJSON")

    report(by_area, points_on_land)
    print(f"\nSaved to {OUT_DIR}/inundation_by_area.csv (+ .geojson)")


if __name__ == "__main__":
    main()
