"""Build a coastal / low-lying flood susceptibility index, and test it.

I combine, per planning area:

  rainfall exposure       = how often the nearest gauge sees heavy-rain days
  terrain susceptibility  = how low-lying and flat the area is

Each is min-max normalised across areas and averaged into a 0–100 index. I assume equal weighting.

WHY THIS IS A COASTAL SUSCEPTIBILITY LAYER, NOT A FLASH-FLOOD PREDICTOR
------------------------------------------------------------------------
I validate the index against the places Singapore actually flash-floods (Bukit
Timah, Geylang, ...). It ranks them LOW. This divergence is the project's key
finding:

  * By rewarding low absolute elevation, the index tracks coastal / reclaimed
    land, so it largely reproduces the sea-level-rise inundation layer, i.e. it
    captures tidal/coastal susceptibility.
  * Singapore's flash floods are driven by drainage capacity and local valley
    micro-topography (Bukit Timah is a runoff-collecting valley that sits at
    *high* absolute elevation). An open 330m DEM cannot resolve any of that.

So, this layer is best read as a coastal-susceptibility complement to the SLR
analysis. Modelling true pluvial flash-flood risk would need drainage-network and
flood-incident data, which is noted as future work. Quantifying *that* gap is the point:
it shows Singapore's flash-flood risk is an infrastructure problem, not a
topography one, which is exactly why PUB invests in drains, not seawalls.

    python -m src.features.flood_index

Outputs:
    data/processed/coastal_susceptibility_by_area.csv
    data/processed/coastal_susceptibility_by_area.geojson   (joined to polygons)
"""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt
from pathlib import Path

import geopandas as gpd
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
RAINFALL_STATS = REPO_ROOT / "data" / "processed" / "rainfall_stats_by_station.csv"
INUNDATION = REPO_ROOT / "data" / "processed" / "inundation_by_area.csv"
BOUNDARIES = REPO_ROOT / "data" / "raw" / "boundaries" / "planning_areas.geojson"
OUT_DIR = REPO_ROOT / "data" / "processed"

SVY21 = 3414  # metric CRS for centroids
RAIN_WEIGHT = 0.5
TERRAIN_WEIGHT = 0.5

# Areas Singapore is actually known to flash-flood — used only to sanity-check
# the index qualitatively, never to fit it.
KNOWN_FLOOD_PRONE = ["Bukit Timah", "Bukit Batok", "Geylang", "Kallang",
                     "Tanglin", "Novena", "Bedok", "Choa Chu Kang"]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(a))


def minmax(s: pd.Series) -> pd.Series:
    """Scale to 0–1; flat series (no spread) maps to 0."""
    lo, hi = s.min(), s.max()
    return (s - lo) / (hi - lo) if hi > lo else s * 0.0


def area_centroids(areas: gpd.GeoDataFrame) -> pd.DataFrame:
    """Lon/lat centroid per planning area (computed in a metric CRS)."""
    cent = areas.to_crs(SVY21).geometry.centroid.to_crs(4326)
    return pd.DataFrame(
        {
            "planning_area": areas["PLN_AREA_N"].str.title().values,
            "centroid_lat": cent.y.values,
            "centroid_lon": cent.x.values,
        }
    )


def assign_nearest_gauge(centroids: pd.DataFrame, gauges: pd.DataFrame) -> pd.DataFrame:
    """Attach each area's nearest rain gauge and that gauge's stats."""
    rows = []
    for _, area in centroids.iterrows():
        d = gauges.apply(
            lambda g: haversine_km(area["centroid_lat"], area["centroid_lon"],
                                   g["latitude"], g["longitude"]),
            axis=1,
        )
        nearest = gauges.loc[d.idxmin()]
        rows.append(
            {
                "planning_area": area["planning_area"],
                "nearest_gauge": nearest["name"],
                "gauge_dist_km": round(d.min(), 1),
                "heavy_days_per_year": nearest["heavy_days_per_year"],
                "max_60min_mm": nearest["max_60min_mm"],
            }
        )
    return pd.DataFrame(rows)


def build_index(areas: gpd.GeoDataFrame, gauges: pd.DataFrame, terrain: pd.DataFrame) -> pd.DataFrame:
    """Join rainfall + terrain per area and compute the 0–100 susceptibility index."""
    rain = assign_nearest_gauge(area_centroids(areas), gauges)
    df = terrain.merge(rain, on="planning_area", how="left")

    # Rainfall exposure: heavy-rain-day frequency at the nearest gauge.
    df["rain_score"] = minmax(df["heavy_days_per_year"])

    # Terrain susceptibility: low-lying (high % <=5 m) and low median elevation.
    lowlying = minmax(df["pct_below_5m"])
    low_elev = minmax(-df["elev_median_m"])
    df["terrain_score"] = (lowlying + low_elev) / 2

    df["susceptibility_index"] = (
        100 * (RAIN_WEIGHT * df["rain_score"] + TERRAIN_WEIGHT * df["terrain_score"])
    ).round(1)
    return df.sort_values("susceptibility_index", ascending=False).reset_index(drop=True)


def report(df: pd.DataFrame) -> None:
    print("\nTop 12 planning areas by coastal/low-lying susceptibility index:")
    cols = ["planning_area", "susceptibility_index", "rain_score", "terrain_score",
            "heavy_days_per_year", "pct_below_5m", "elev_median_m"]
    print(df[cols].head(12).round(2).to_string(index=False))

    print("\nValidation against actual flash-flood spots (rank / 55):")
    print("  -> Expect these to rank LOW. That is the finding: this index measures")
    print("     coastal/low-lying susceptibility, not drainage-driven flash floods.")
    df = df.reset_index(drop=True)
    for area in KNOWN_FLOOD_PRONE:
        hit = df.index[df["planning_area"] == area]
        if len(hit):
            i = hit[0]
            r = df.loc[i]
            print(f"  {area:<14} rank {i + 1:>2}/55  index {r['susceptibility_index']:>5}")


def main() -> None:
    areas = gpd.read_file(BOUNDARIES)
    gauges = pd.read_csv(RAINFALL_STATS)
    terrain = pd.read_csv(INUNDATION)

    df = build_index(areas, gauges, terrain)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_DIR / "coastal_susceptibility_by_area.csv", index=False)

    geo = areas.assign(planning_area=areas["PLN_AREA_N"].str.title()).merge(
        df.drop(columns="region", errors="ignore"), on="planning_area", how="left"
    )
    geo.to_file(OUT_DIR / "coastal_susceptibility_by_area.geojson", driver="GeoJSON")

    report(df)
    print(f"\nSaved to {OUT_DIR}/coastal_susceptibility_by_area.csv (+ .geojson)")


if __name__ == "__main__":
    main()
