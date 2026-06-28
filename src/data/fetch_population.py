"""Download resident population per planning area (Census 2020, data.gov.sg).

This feeds the economic-exposure layer: once we know how much of each planning
area floods, population tells us how many people that actually affects.

The source table lists subzones grouped under each planning area, with a
"<Area> - Total" row per area and a single national "Total" row. I keep only the
per-area totals.

    python -m src.data.fetch_population

Output:
    data/raw/population/population_by_area.csv   [planning_area, population]
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pandas as pd
import requests

POLL_URL = "https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/poll-download"

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "configs" / "population.json"
OUT_DIR = REPO_ROOT / "data" / "raw" / "population"


def download_csv(dataset_id: str) -> pd.DataFrame:
    """Resolve the presigned URL and read the census CSV."""
    url = POLL_URL.format(dataset_id=dataset_id)
    download_url = requests.get(url, timeout=30).json()["data"]["url"]
    # Use requests (certifi-backed) rather than letting pandas open the URL via
    # urllib, which fails SSL verification on this Python build.
    resp = requests.get(download_url, timeout=60)
    resp.raise_for_status()
    return pd.read_csv(io.StringIO(resp.text))


def extract_area_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only the per-planning-area total rows; drop subzones and the national total."""
    totals = df[df["Number"].str.endswith(" - Total")].copy()
    totals["planning_area"] = (
        totals["Number"].str.replace(" - Total", "", regex=False).str.title()
    )
    totals["population"] = pd.to_numeric(totals["Total_Total"], errors="coerce").astype("Int64")
    return totals[["planning_area", "population"]].reset_index(drop=True)


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text())
    print(f"Fetching '{config['name']}' from data.gov.sg...")

    df = download_csv(config["dataset_id"])
    areas = extract_area_totals(df)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "population_by_area.csv"
    areas.to_csv(out_path, index=False)

    print(f"Planning areas with residents: {len(areas)}")
    print(f"Total resident population: {int(areas['population'].sum()):,}")
    print("\nMost populous areas:")
    print(areas.sort_values("population", ascending=False).head(8).to_string(index=False))
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
