"""Sample a ground-elevation grid over Singapore from OpenTopoData (SRTM 30 m).

Elevation is the backbone of the sea-level-rise story: to say what floods at
+1 m / +2 m / +5 m, I first need to know how high each patch of land sits.

I sample a regular lat/lon grid across the area of interest (configs/aoi.json)
and ask OpenTopoData for the SRTM elevation at each point.

    python -m src.data.fetch_elevation

Output:
    data/raw/elevation/elevation_grid.csv   columns [latitude, longitude, elevation_m]

Note: SRTM reports water surfaces as ~0 m, so points over sea/reservoirs show up
as very low. I keep them as-is here and clip to land later, when I add the
coastline/planning-area boundaries.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import requests

OPENTOPO_URL = "https://api.opentopodata.org/v1/srtm30m"
BATCH_SIZE = 100          # max locations the free API accepts per request
SLEEP_BETWEEN_CALLS = 1.1  # seconds; free tier allows 1 call/sec, leave a margin

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "configs" / "aoi.json"
OUT_DIR = REPO_ROOT / "data" / "raw" / "elevation"


def frange(start: float, stop: float, step: float) -> list[float]:
    """Inclusive float range, rounded to avoid floating-point drift in coords."""
    n = int(round((stop - start) / step))
    return [round(start + i * step, 6) for i in range(n + 1)]


def build_grid(bbox: dict, spacing: float) -> list[tuple[float, float]]:
    """Return every (lat, lon) point on the regular grid covering the bbox."""
    lats = frange(bbox["lat_min"], bbox["lat_max"], spacing)
    lons = frange(bbox["lon_min"], bbox["lon_max"], spacing)
    return [(lat, lon) for lat in lats for lon in lons]


def fetch_batch(points: list[tuple[float, float]], session: requests.Session) -> list[float | None]:
    """Query elevation for up to BATCH_SIZE points; returns one value per point."""
    locations = "|".join(f"{lat},{lon}" for lat, lon in points)
    resp = session.get(OPENTOPO_URL, params={"locations": locations}, timeout=60)
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("status") != "OK":
        raise RuntimeError(f"OpenTopoData error: {payload.get('error')!r}")
    return [r["elevation"] for r in payload["results"]]


def fetch_elevation_grid(grid: list[tuple[float, float]]) -> pd.DataFrame:
    """Fetch elevation for the whole grid, batching and rate-limiting politely."""
    session = requests.Session()
    rows = []
    n_batches = (len(grid) + BATCH_SIZE - 1) // BATCH_SIZE

    for b in range(n_batches):
        batch = grid[b * BATCH_SIZE : (b + 1) * BATCH_SIZE]
        elevations = fetch_batch(batch, session)
        for (lat, lon), elev in zip(batch, elevations):
            rows.append({"latitude": lat, "longitude": lon, "elevation_m": elev})
        print(f"  batch {b + 1}/{n_batches} done ({len(rows)} points)", flush=True)
        if b < n_batches - 1:
            time.sleep(SLEEP_BETWEEN_CALLS)

    return pd.DataFrame(rows)


def summarise(df: pd.DataFrame) -> None:
    """Print a quick low-lying summary — the numbers that drive the SLR layer."""
    elev = df["elevation_m"].dropna()
    print(f"\nGrid points: {len(df)}  (valid elevations: {len(elev)})")
    print(f"Elevation range: {elev.min():.0f} m to {elev.max():.0f} m")
    for threshold in (1, 2, 5):
        share = (elev <= threshold).mean() * 100
        print(f"  <= {threshold} m: {share:.1f}% of sampled points")
    print("(Includes sea/reservoir points read as ~0 m — we clip to land later.)")


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text())
    grid = build_grid(config["bbox"], config["grid_spacing_deg"])
    print(f"Sampling {len(grid)} grid points over '{config['name']}' "
          f"(~{config['grid_spacing_deg']} deg spacing)...")

    df = fetch_elevation_grid(grid)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "elevation_grid.csv"
    df.to_csv(out_path, index=False)

    summarise(df)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
