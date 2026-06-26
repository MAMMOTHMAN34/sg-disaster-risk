"""Collect historical daily rainfall per station from the weather.gov.sg archive.

The live rainfall API only gives a 5-minute snapshot. For a flood-risk index I
need the *history*: which parts of the island get the most frequent and most
intense rain. The Meteorological Service publishes per-station monthly CSVs with
each day's rainfall total and its highest 30 / 60 / 120-minute intensity. Short, intense bursts are what actually cause Singapore's flash floods.

The archive needs a browser User-Agent (it 403s otherwise), and only ~40 of the
76 live gauges have deep history, so I pre-filter to stations that return data
before downloading their full range. The pull is resumable per station: a
station whose output CSV already exists is skipped, so an interrupted run just
continues.

    python -m src.data.fetch_rainfall_history

Outputs:
    data/raw/rainfall_history/stations.csv      id, name, lat, lon (all live gauges)
    data/raw/rainfall_history/<station_id>.csv  daily rows for one station
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import requests

RAINFALL_API = "https://api-open.data.gov.sg/v2/real-time/api/rainfall"
ARCHIVE_URL = "https://www.weather.gov.sg/files/dailydata/DAILYDATA_{sid}_{ym}.csv"
HEADERS = {"User-Agent": "Mozilla/5.0"}  # archive rejects the default requests UA

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "configs" / "rainfall_history.json"
OUT_DIR = REPO_ROOT / "data" / "raw" / "rainfall_history"

# Months to probe when deciding whether a station has usable history at all.
PROBE_MONTHS = ("202501", "201501", "202012")


def get_stations(session: requests.Session) -> pd.DataFrame:
    """Pull the live gauge list (id, name, coordinates) from data.gov.sg."""
    data = session.get(RAINFALL_API, timeout=30).json()["data"]
    rows = [
        {
            "station_id": s["id"],
            "name": s["name"],
            "latitude": s["location"]["latitude"],
            "longitude": s["location"]["longitude"],
        }
        for s in data["stations"]
    ]
    return pd.DataFrame(rows)


def fetch_month(session: requests.Session, sid: str, ym: str) -> list[dict]:
    """Download and parse one station-month. Returns [] if missing/empty.

    We parse only the first 8 columns (Station, Y, M, D, rainfall total, and the
    30/60/120-min highs), all ASCII, to sidestep the file's non-UTF8 °C header.
    """
    resp = session.get(ARCHIVE_URL.format(sid=sid, ym=ym), timeout=30)
    if resp.status_code != 200:
        return []
    lines = resp.text.splitlines()
    if len(lines) < 2:
        return []

    def num(x: str) -> float | None:
        try:
            return float(x.strip())
        except ValueError:
            return None  # archive uses "-"/"" for missing days

    rows = []
    for line in lines[1:]:
        c = line.split(",")
        if len(c) < 8:
            continue
        try:
            date = pd.Timestamp(year=int(c[1]), month=int(c[2]), day=int(c[3]))
        except (ValueError, IndexError):
            continue
        rows.append(
            {
                "station_id": sid,
                "date": date,
                "rainfall_mm": num(c[4]),
                "rain_max_30min_mm": num(c[5]),
                "rain_max_60min_mm": num(c[6]),
                "rain_max_120min_mm": num(c[7]),
            }
        )
    return rows


def station_has_history(session: requests.Session, sid: str) -> bool:
    """True if the station returns data for any probe month."""
    return any(fetch_month(session, sid, ym) for ym in PROBE_MONTHS)


def fetch_station_history(session: requests.Session, sid: str, years: range, delay: float) -> pd.DataFrame:
    """Download every available month for one station and stack into a frame."""
    rows = []
    for year in years:
        for month in range(1, 13):
            rows.extend(fetch_month(session, sid, f"{year}{month:02d}"))
            time.sleep(delay)
    return pd.DataFrame(rows)


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text())
    years = range(config["year_start"], config["year_end"] + 1)
    delay = config["request_delay_s"]

    session = requests.Session()
    session.headers.update(HEADERS)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stations = get_stations(session)
    stations.to_csv(OUT_DIR / "stations.csv", index=False)
    print(f"{len(stations)} live gauges. Checking which have historical data...")

    for _, st in stations.iterrows():
        sid = st["station_id"]
        out_path = OUT_DIR / f"{sid}.csv"
        if out_path.exists():
            print(f"  {sid}: already downloaded, skipping")
            continue
        if not station_has_history(session, sid):
            print(f"  {sid}: no archive history, skipping")
            continue

        df = fetch_station_history(session, sid, years, delay)
        df.to_csv(out_path, index=False)
        rain_days = int((df["rainfall_mm"] > 0).sum())
        print(f"  {sid} ({st['name']}): {len(df)} days "
              f"[{df['date'].min().date()}..{df['date'].max().date()}], {rain_days} rain days")

    print("Done.")


if __name__ == "__main__":
    main()
