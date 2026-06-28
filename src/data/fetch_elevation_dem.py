"""Sample elevation from the Copernicus GLO-30 DEM (~2013) for Singapore.

This replaced an earlier SRTM/OpenTopoData sampler for the coastal analysis.
SRTM was captured in 2000, so it sees land reclaimed since then (Jurong Island,
Tuas, parts of Changi) as open sea (height 0), which made those
areas falsely "flood" in the sea-level-rise scenarios. Copernicus GLO-30 was
captured around 2013, so it includes that reclamation and gives accurate heights.

It writes the same file as the old sampler (data/raw/elevation/elevation_grid.csv,
columns latitude/longitude/elevation_m), so every downstream layer (inundation,
SLR scenarios, and susceptibility) re-runs unchanged. Since reading a raster has no
API limit, I sample a finer grid (configs/aoi.json -> dem_grid_spacing_deg).

Limits that remain: Copernicus is a surface model (includes building and
tree heights), and 2013 predates the very newest reclamation (e.g. Tuas mega port).

    python -m src.data.fetch_elevation_dem

Outputs:
    data/raw/elevation/dem/<tile>.tif        downloaded once, reused
    data/raw/elevation/elevation_grid.csv    latitude, longitude, elevation_m
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import rasterio
import requests

# Free, no-key Copernicus GLO-30 tiles covering Singapore (1°×1° each).
BASE = "https://copernicus-dem-30m.s3.amazonaws.com"
TILES = {
    "N01_E103": f"{BASE}/Copernicus_DSM_COG_10_N01_00_E103_00_DEM/Copernicus_DSM_COG_10_N01_00_E103_00_DEM.tif",
    "N01_E104": f"{BASE}/Copernicus_DSM_COG_10_N01_00_E104_00_DEM/Copernicus_DSM_COG_10_N01_00_E104_00_DEM.tif",
}

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "configs" / "aoi.json"
ELEV_DIR = REPO_ROOT / "data" / "raw" / "elevation"
DEM_DIR = ELEV_DIR / "dem"


def download_tiles() -> list[Path]:
    """Download each DEM tile once; reuse on later runs."""
    DEM_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, url in TILES.items():
        path = DEM_DIR / f"{name}.tif"
        if not path.exists():
            print(f"  downloading {name} ...", flush=True)
            resp = requests.get(url, timeout=600)
            resp.raise_for_status()
            path.write_bytes(resp.content)
        paths.append(path)
    return paths


def frange(start: float, stop: float, step: float) -> list[float]:
    n = int(round((stop - start) / step))
    return [round(start + i * step, 6) for i in range(n + 1)]


def build_grid(bbox: dict, spacing: float) -> list[tuple[float, float]]:
    lats = frange(bbox["lat_min"], bbox["lat_max"], spacing)
    lons = frange(bbox["lon_min"], bbox["lon_max"], spacing)
    return [(lat, lon) for lat in lats for lon in lons]


def sample_grid(grid: list[tuple[float, float]], tile_paths: list[Path]) -> pd.DataFrame:
    """Look up each grid point's elevation in whichever tile contains it."""
    elevations: list[float | None] = [None] * len(grid)
    datasets = [rasterio.open(p) for p in tile_paths]
    try:
        for ds in datasets:
            b = ds.bounds
            idx = [
                i for i, (lat, lon) in enumerate(grid)
                if elevations[i] is None and b.left <= lon <= b.right and b.bottom <= lat <= b.top
            ]
            coords = [(grid[i][1], grid[i][0]) for i in idx]  # rasterio wants (x=lon, y=lat)
            for i, val in zip(idx, ds.sample(coords)):
                v = float(val[0])
                elevations[i] = None if (ds.nodata is not None and v == ds.nodata) else round(v, 1)
    finally:
        for ds in datasets:
            ds.close()

    return pd.DataFrame(
        {
            "latitude": [lat for lat, _ in grid],
            "longitude": [lon for _, lon in grid],
            "elevation_m": elevations,
        }
    )


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text())
    spacing = config.get("dem_grid_spacing_deg", 0.001)

    print("Fetching Copernicus GLO-30 tiles...")
    tile_paths = download_tiles()

    grid = build_grid(config["bbox"], spacing)
    print(f"Sampling {len(grid)} grid points (~{spacing} deg) from the DEM...")
    df = sample_grid(grid, tile_paths)

    out_path = ELEV_DIR / "elevation_grid.csv"
    df.to_csv(out_path, index=False)

    elev = df["elevation_m"].dropna()
    print(f"\nGrid points: {len(df)}  (valid: {len(elev)})")
    print(f"Elevation range: {elev.min():.0f} m to {elev.max():.0f} m")
    for t in (1, 2, 5):
        print(f"  <= {t} m: {(elev <= t).mean() * 100:.1f}% of sampled points (incl. sea)")
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
