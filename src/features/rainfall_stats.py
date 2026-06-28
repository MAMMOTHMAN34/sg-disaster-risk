"""Summarise each rain gauge's 2009–2025 history into a climatology table.

The flood-risk index needs a stable per-station picture of *how much* and *how
hard* it rains. From the daily history I compute, per station:

  - mean annual rainfall (total wetness)
  - heavy-rain days per year (>= 50 mm) and very-heavy days (>= 100 mm)
  - the wettest single day on record
  - typical and extreme 60-minute intensity, where the gauge logs it

Heavy-day frequency and short-burst intensity matter more for flash flooding
than the annual total: Singapore floods when a lot of rain falls *fast*, not
when the year is merely wet.

    python -m src.features.rainfall_stats

Output:
    data/processed/rainfall_stats_by_station.csv
"""

from __future__ import annotations

import glob
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORY_DIR = REPO_ROOT / "data" / "raw" / "rainfall_history"
OUT_PATH = REPO_ROOT / "data" / "processed" / "rainfall_stats_by_station.csv"

HEAVY_MM = 50        # PUB-ish "heavy rain" day
VERY_HEAVY_MM = 100  # exceptional daily fall
MIN_DAYS_PER_YEAR = 300  # only count years with near-complete coverage


def load_history() -> pd.DataFrame:
    """Concatenate every per-station daily CSV into one frame."""
    files = [f for f in glob.glob(str(HISTORY_DIR / "S*.csv")) if "stations" not in f]
    frames = [pd.read_csv(f, parse_dates=["date"]) for f in files]
    return pd.concat(frames, ignore_index=True)


def station_stats(daily: pd.DataFrame) -> pd.DataFrame:
    """Reduce daily rows to one climatology row per station."""
    daily = daily.copy()
    daily["year"] = daily["date"].dt.year

    rows = []
    for sid, g in daily.groupby("station_id"):
        rain = g["rainfall_mm"]

        # Mean annual rainfall: total per year, averaged over well-covered years
        # so partial years at the start/end of a gauge's life don't bias it.
        per_year = g.dropna(subset=["rainfall_mm"]).groupby("year")["rainfall_mm"]
        complete_years = per_year.count()[lambda s: s >= MIN_DAYS_PER_YEAR].index
        annual_totals = per_year.sum().loc[complete_years]
        mean_annual = annual_totals.mean() if not annual_totals.empty else float("nan")

        n_years = max(len(complete_years), 1)
        rows.append(
            {
                "station_id": sid,
                "n_complete_years": len(complete_years),
                "mean_annual_rainfall_mm": round(mean_annual, 0),
                "heavy_days_per_year": round((rain >= HEAVY_MM).sum() / n_years, 1),
                "very_heavy_days_per_year": round((rain >= VERY_HEAVY_MM).sum() / n_years, 2),
                "max_daily_mm": round(rain.max(), 1),
                "max_60min_mm": round(g["rain_max_60min_mm"].max(), 1),
                "p95_60min_on_rain_days_mm": round(
                    g.loc[rain > 0.2, "rain_max_60min_mm"].quantile(0.95), 1
                ),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    daily = load_history()
    stats = station_stats(daily)

    # Attach gauge names + coordinates for the later nearest-station join.
    meta = pd.read_csv(HISTORY_DIR / "stations.csv")
    stats = stats.merge(meta, on="station_id", how="left")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    stats.sort_values("heavy_days_per_year", ascending=False).to_csv(OUT_PATH, index=False)

    print(f"Stations summarised: {len(stats)}")
    print(f"Mean annual rainfall across gauges: "
          f"{stats['mean_annual_rainfall_mm'].mean():.0f} mm "
          f"(range {stats['mean_annual_rainfall_mm'].min():.0f}–{stats['mean_annual_rainfall_mm'].max():.0f})")
    print("\nWettest gauges by heavy-rain days/year (>= 50 mm):")
    cols = ["name", "heavy_days_per_year", "very_heavy_days_per_year", "mean_annual_rainfall_mm", "max_daily_mm"]
    print(stats.sort_values("heavy_days_per_year", ascending=False)[cols].head(10).to_string(index=False))
    print(f"\nSaved to {OUT_PATH}")


if __name__ == "__main__":
    main()
