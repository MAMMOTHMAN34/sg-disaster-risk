"""Download Singapore's planning-area boundaries (GeoJSON) from data.gov.sg.

These 55 URA planning areas are the spatial unit the whole project hangs on:
they let me clip the elevation grid to land (dropping the sea points that made
the raw "% below 1 m" misleading) and later aggregate every hazard into a single
risk score per area for the dashboard.

data.gov.sg serves file datasets through a "poll-download" API that hands back a
short-lived presigned S3 URL, so I ask for the URL, then download the file.

    python -m src.data.fetch_boundaries

Output:
    data/raw/boundaries/planning_areas.geojson   (55 land polygons)
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import requests

POLL_URL_TEMPLATE = "https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/poll-download"

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "configs" / "boundaries.json"
OUT_DIR = REPO_ROOT / "data" / "raw" / "boundaries"


def get_download_url(dataset_id: str, attempts: int = 5, wait: float = 2.0) -> str:
    """Ask data.gov.sg for the presigned download URL, retrying if not ready.

    The dataset is pre-generated, so the URL is usually returned on the first
    call — but the API can briefly return an empty URL, so we poll a few times.
    """
    url = POLL_URL_TEMPLATE.format(dataset_id=dataset_id)
    for attempt in range(1, attempts + 1):
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        download_url = payload.get("data", {}).get("url")
        if download_url:
            return download_url
        print(f"  url not ready (attempt {attempt}/{attempts}), waiting...")
        time.sleep(wait)
    raise RuntimeError(f"data.gov.sg never returned a download URL for {dataset_id}")


def download(url: str, dest: Path) -> None:
    """Stream the GeoJSON file to disk."""
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    dest.write_bytes(resp.content)


def summarise(path: Path) -> None:
    """Print how many areas and regions we got — a quick integrity check."""
    data = json.loads(path.read_text())
    feats = data["features"]
    names = sorted(f["properties"]["PLN_AREA_N"].title() for f in feats)
    regions = sorted({f["properties"]["REGION_N"].title() for f in feats})
    print(f"\nPlanning areas: {len(feats)}")
    print(f"Regions: {', '.join(regions)}")
    print(f"Sample areas: {', '.join(names[:8])} ...")


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text())
    print(f"Fetching '{config['name']}' from data.gov.sg...")

    download_url = get_download_url(config["dataset_id"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "planning_areas.geojson"
    download(download_url, out_path)

    summarise(out_path)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
