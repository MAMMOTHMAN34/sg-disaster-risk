"""Sea-level-rise scenarios: how much of each area floods as the sea rises.

The inundation layer measured generic low-lying land. This turns that into the
concrete question a normal person asks: "if the sea rises this much, what goes
under?" Using Singapore's own official projections:

    +1m  : central estimate for 2100
    +2m  : central estimate for 2150
    +4m  : worst case (high mean sea level + storm surge + high tide together)

For each planning area and for the island as a whole, I report the land area (km²)
and share that sits at or below each level. Each elevation grid point stands for
an equal patch of ground, so the share of an area's points below a level, times
the area's true land area, estimates the flooded land.

    python -m src.features.slr_scenarios

Outputs:
    data/processed/slr_scenarios_by_area.csv
    data/processed/slr_scenarios_by_area.geojson   (joined to polygons, for maps)
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
ELEVATION_CSV = REPO_ROOT / "data" / "raw" / "elevation" / "elevation_grid.csv"
BOUNDARIES = REPO_ROOT / "data" / "raw" / "boundaries" / "planning_areas.geojson"
OUT_DIR = REPO_ROOT / "data" / "processed"

WGS84, SVY21 = 4326, 3414

# Named scenarios -> sea-level rise in metres. Land at/below this floods.
SCENARIOS = {
    "y2100_1m": 1,
    "y2150_2m": 2,
    "worstcase_4m": 4,
}


def load_points() -> gpd.GeoDataFrame:
    df = pd.read_csv(ELEVATION_CSV)
    return gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df["longitude"], df["latitude"]), crs=WGS84
    )


def points_on_land(points: gpd.GeoDataFrame, areas: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Tag each elevation point with its planning area; sea points are dropped."""
    a = areas[["PLN_AREA_N", "geometry"]].rename(columns={"PLN_AREA_N": "planning_area"})
    joined = gpd.sjoin(points, a, how="inner", predicate="within")
    joined["planning_area"] = joined["planning_area"].str.title()
    return joined


def land_area_km2(areas: gpd.GeoDataFrame) -> pd.Series:
    m = areas.to_crs(SVY21)
    return pd.Series(
        (m.geometry.area / 1e6).values,
        index=areas["PLN_AREA_N"].str.title().values,
    )


def build_scenarios(land: gpd.GeoDataFrame, area_km2: pd.Series) -> pd.DataFrame:
    """Per area: flooded km² and % of land at each sea-level scenario."""
    rows = []
    for area, elev in land.groupby("planning_area")["elevation_m"]:
        total_km2 = float(area_km2.get(area, float("nan")))
        row = {"planning_area": area, "land_area_km2": round(total_km2, 2)}
        for name, level in SCENARIOS.items():
            share = (elev <= level).mean()
            row[f"pct_{name}"] = round(share * 100, 1)
            row[f"flooded_km2_{name}"] = round(share * total_km2, 2)
        rows.append(row)
    df = pd.DataFrame(rows)
    return df.sort_values("flooded_km2_y2150_2m", ascending=False).reset_index(drop=True)


def report(df: pd.DataFrame) -> None:
    total_land = df["land_area_km2"].sum()
    print(f"\nIsland-wide flooded land by scenario (of {total_land:.0f} km² land):")
    for name, level in SCENARIOS.items():
        flooded = df[f"flooded_km2_{name}"].sum()
        print(f"  +{level} m ({name}): {flooded:.0f} km²  "
              f"({flooded / total_land * 100:.1f}% of land)")

    print("\nMost-exposed areas at +2 m (2150 central estimate):")
    cols = ["planning_area", "land_area_km2", "flooded_km2_y2150_2m", "pct_y2150_2m"]
    print(df[cols].head(10).to_string(index=False))


def main() -> None:
    areas = gpd.read_file(BOUNDARIES)
    land = points_on_land(load_points(), areas)
    df = build_scenarios(land, land_area_km2(areas))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_DIR / "slr_scenarios_by_area.csv", index=False)

    geo = areas.assign(planning_area=areas["PLN_AREA_N"].str.title()).merge(
        df, on="planning_area", how="left"
    )
    geo.to_file(OUT_DIR / "slr_scenarios_by_area.geojson", driver="GeoJSON")

    report(df)
    print(f"\nSaved to {OUT_DIR}/slr_scenarios_by_area.csv (+ .geojson)")


if __name__ == "__main__":
    main()
