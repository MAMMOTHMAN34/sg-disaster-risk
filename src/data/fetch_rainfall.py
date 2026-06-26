"""Fetch live rainfall readings from Singapore's open data API (data.gov.sg).

The endpoint returns a 5-minute snapshot from ~76 NEA rain gauges across the
island, each with coordinates. This is the backbone of the flood-risk side of
the project: rainfall intensity is the trigger, terrain decides where it pools.

Run it directly to grab the current snapshot:

    python -m src.data.fetch_rainfall

Output:
    data/raw/rainfall/stations.csv              one row per gauge (id, name, lat, lon)
    data/raw/rainfall/readings_<timestamp>.csv  one row per gauge for this snapshot
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

# data.gov.sg v2 real-time environment API. No API key required.
RAINFALL_URL = "https://api-open.data.gov.sg/v2/real-time/api/rainfall"

# Resolve paths relative to the repo root, not the caller's working directory,
# so the script behaves the same no matter where you run it from.
REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "data" / "raw" / "rainfall"


def fetch_rainfall(url: str = RAINFALL_URL, timeout: int = 30) -> dict:
    """Call the API and return the parsed JSON `data` block.

    Raises on any HTTP error or non-zero API status code so failures are loud
    rather than silently producing empty files.
    """
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("code") != 0:
        raise RuntimeError(f"API returned error: {payload.get('errorMsg')!r}")
    return payload["data"]


def to_frames(data: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split the API response into a station table and a readings table.

    Returns
    -------
    stations : DataFrame  columns [station_id, name, latitude, longitude]
    readings : DataFrame  columns [station_id, timestamp, rainfall_mm]
    """
    stations = pd.json_normalize(data["stations"]).rename(
        columns={
            "id": "station_id",
            "location.latitude": "latitude",
            "location.longitude": "longitude",
        }
    )[["station_id", "name", "latitude", "longitude"]]

    # `readings` is a list of snapshots; the real-time feed normally holds one.
    rows = []
    for snapshot in data["readings"]:
        ts = snapshot["timestamp"]
        for r in snapshot["data"]:
            rows.append(
                {"station_id": r["stationId"], "timestamp": ts, "rainfall_mm": r["value"]}
            )
    readings = pd.DataFrame(rows)

    return stations, readings


def save(stations: pd.DataFrame, readings: pd.DataFrame, out_dir: Path = OUT_DIR) -> None:
    """Write the station list and a timestamped readings snapshot to disk."""
    out_dir.mkdir(parents=True, exist_ok=True)

    # The station list is stable, so we just keep overwriting the latest copy.
    stations.to_csv(out_dir / "stations.csv", index=False)

    # Readings are a point-in-time snapshot — stamp the filename so repeated runs
    # accumulate a history we can later stitch into a time series.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    readings.to_csv(out_dir / f"readings_{stamp}.csv", index=False)


def main() -> None:
    data = fetch_rainfall()
    stations, readings = to_frames(data)
    save(stations, readings)

    wet = readings[readings["rainfall_mm"] > 0]
    print(f"Fetched {len(stations)} stations, {len(readings)} readings.")
    print(f"Stations reporting rain right now: {len(wet)}")
    if not wet.empty:
        top = wet.sort_values("rainfall_mm", ascending=False).head(5)
        merged = top.merge(stations[["station_id", "name"]], on="station_id")
        for _, row in merged.iterrows():
            print(f"  {row['rainfall_mm']:>5.1f} mm  {row['name']}")
    print(f"Saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
