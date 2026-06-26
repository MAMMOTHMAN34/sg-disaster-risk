"""Pull historical earthquakes around the Sunda Megathrust from the USGS API.

This feeds the project's *tail-risk layer*. Singapore does not sit on a plate
boundary, so it generates no quakes of its own, but large events on the Sunda
Megathrust off Sumatra (and in the Andaman Sea) are felt here, and are the
sources behind the low-probability tsunami risk. Thus, I should frame it as "how
much seismic energy is released near Singapore, and how far away", not "will
Singapore have an earthquake".

I query the USGS FDSN event service for the region and filters in
configs/seismic.json, then add each event's great-circle distance to Singapore.

    python -m src.data.fetch_seismic

Output:
    data/raw/seismic/earthquakes.csv
        columns [time, magnitude, place, depth_km, latitude, longitude,
                 distance_to_sg_km, usgs_id]
"""

from __future__ import annotations

import json
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

import pandas as pd
import requests

USGS_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"

# Singapore's approximate centroid — the reference point for distances.
SG_LAT, SG_LON = 1.3521, 103.8198
EARTH_RADIUS_KM = 6371.0

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "configs" / "seismic.json"
OUT_DIR = REPO_ROOT / "data" / "raw" / "seismic"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in kilometres."""
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(a))


def fetch_events(config: dict) -> dict:
    """Call the USGS FDSN event service and return the parsed GeoJSON."""
    region = config["region"]
    params = {
        "format": "geojson",
        "starttime": config["start_date"],
        "minmagnitude": config["min_magnitude"],
        "minlatitude": region["lat_min"],
        "maxlatitude": region["lat_max"],
        "minlongitude": region["lon_min"],
        "maxlongitude": region["lon_max"],
        "orderby": "time",
    }
    resp = requests.get(USGS_URL, params=params, timeout=120)
    resp.raise_for_status()
    return resp.json()


def to_frame(geojson: dict) -> pd.DataFrame:
    """Flatten USGS GeoJSON features into a tidy table with distance-to-SG."""
    rows = []
    for feat in geojson["features"]:
        props = feat["properties"]
        lon, lat, depth_km = feat["geometry"]["coordinates"]  # GeoJSON is lon,lat,depth
        rows.append(
            {
                # USGS time is epoch milliseconds, UTC.
                "time": pd.to_datetime(props["time"], unit="ms", utc=True),
                "magnitude": props["mag"],
                "place": props["place"],
                "depth_km": depth_km,
                "latitude": lat,
                "longitude": lon,
                "distance_to_sg_km": round(haversine_km(SG_LAT, SG_LON, lat, lon), 1),
                "usgs_id": feat["id"],
            }
        )
    return pd.DataFrame(rows).sort_values("time").reset_index(drop=True)


def summarise(df: pd.DataFrame) -> None:
    """Print the framing numbers: how big, how close, how often the rare ones."""
    print(f"\nEvents: {len(df)}  ({df['time'].dt.year.min()}–{df['time'].dt.year.max()})")
    for m in (5, 6, 7, 8):
        print(f"  M>= {m}: {(df['magnitude'] >= m).sum()}")

    biggest = df.loc[df["magnitude"].idxmax()]
    print(f"\nLargest: M{biggest['magnitude']} — {biggest['place']}")
    print(f"         {biggest['distance_to_sg_km']:.0f} km from Singapore "
          f"({biggest['time'].date()})")

    # Closest large event (M>=7) — the most relevant to a "felt in SG" story.
    big = df[df["magnitude"] >= 7]
    if not big.empty:
        nearest = big.loc[big["distance_to_sg_km"].idxmin()]
        print(f"Closest M>=7: M{nearest['magnitude']} — {nearest['place']}")
        print(f"         {nearest['distance_to_sg_km']:.0f} km from Singapore "
              f"({nearest['time'].date()})")


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text())
    print(f"Querying USGS for M>={config['min_magnitude']} events since "
          f"{config['start_date']} in the Sunda/Andaman region...")

    geojson = fetch_events(config)
    df = to_frame(geojson)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "earthquakes.csv"
    df.to_csv(out_path, index=False)

    summarise(df)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
