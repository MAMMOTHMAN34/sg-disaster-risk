"""Is Singapore's heavy rain actually getting worse? A 17-year trend check.

The README (citing the government's climate study which uses 40+ years of data) says rainfall is intensifying.
However, I only have the gauge archive back to 2009.

For each year I compute island-average metrics (averaged per station so a growing
number of gauges doesn't bias the trend):

    annual rainfall, heavy-rain days (>=50 mm), very-heavy days (>=100 mm),
    and yearly peak 60-minute intensity.

Then, I fit a simple straight-line trend to each and report the slope per decade
and its p-value.

CAVEAT: 17 years is short for climate. The series is dominated by
El Niño / La Niña swings (e.g. the 2015 El Niño drought), so a non-significant
trend here does NOT contradict the longer official record. It just means my
window is too short to resolve it.

    python -m src.features.rainfall_trend

Outputs:
    data/processed/rainfall_trend_by_year.csv
    reports/figures/rainfall_trend.png
"""

from __future__ import annotations

import glob
from pathlib import Path

import pandas as pd
from scipy import stats

import matplotlib
matplotlib.use("Agg")  # no display needed; we save to file
import matplotlib.pyplot as plt  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORY_DIR = REPO_ROOT / "data" / "raw" / "rainfall_history"
OUT_CSV = REPO_ROOT / "data" / "processed" / "rainfall_trend_by_year.csv"
FIG_PATH = REPO_ROOT / "reports" / "figures" / "rainfall_trend.png"

HEAVY_MM, VERY_HEAVY_MM = 50, 100
MIN_DAYS_PER_YEAR = 300  # only count near-complete station-years


def load_history() -> pd.DataFrame:
    files = [f for f in glob.glob(str(HISTORY_DIR / "S*.csv")) if "stations" not in f]
    df = pd.concat([pd.read_csv(f, parse_dates=["date"]) for f in files], ignore_index=True)
    df["year"] = df["date"].dt.year
    return df


def yearly_island_metrics(daily: pd.DataFrame) -> pd.DataFrame:
    """Average each metric across gauges, per year (robust to gauge count)."""
    by_sy = daily.groupby(["station_id", "year"]).agg(
        days=("rainfall_mm", "count"),
        annual_total=("rainfall_mm", "sum"),
        heavy=("rainfall_mm", lambda s: (s >= HEAVY_MM).sum()),
        very_heavy=("rainfall_mm", lambda s: (s >= VERY_HEAVY_MM).sum()),
        peak_60min=("rain_max_60min_mm", "max"),
    )
    by_sy = by_sy[by_sy["days"] >= MIN_DAYS_PER_YEAR]  # complete station-years only

    out = by_sy.groupby("year").agg(
        n_gauges=("annual_total", "size"),
        annual_rainfall_mm=("annual_total", "mean"),
        heavy_days=("heavy", "mean"),
        very_heavy_days=("very_heavy", "mean"),
        peak_60min_mm=("peak_60min", "mean"),
    ).round(1)
    return out.reset_index()


def trend(years: pd.Series, values: pd.Series) -> dict:
    """Straight-line fit; report change per decade and significance."""
    mask = values.notna()  # some early years lack 60-min intensity data
    res = stats.linregress(years[mask], values[mask])
    return {
        "per_decade": round(res.slope * 10, 2),
        "p_value": round(res.pvalue, 3),
        "significant": res.pvalue < 0.05,
    }


METRICS = {
    "annual_rainfall_mm": "Annual rainfall (mm)",
    "heavy_days": "Heavy-rain days/yr (>=50 mm)",
    "very_heavy_days": "Very-heavy days/yr (>=100 mm)",
    "peak_60min_mm": "Peak 60-min intensity (mm)",
}


def report(yearly: pd.DataFrame) -> None:
    print(f"Years: {yearly['year'].min()}–{yearly['year'].max()} "
          f"({yearly['n_gauges'].min()}–{yearly['n_gauges'].max()} gauges/yr)\n")
    print("Trend per decade (2009–2025):")
    for col, label in METRICS.items():
        t = trend(yearly["year"], yearly[col])
        verdict = "significant" if t["significant"] else "NOT significant (too short / noisy)"
        print(f"  {label:<32} {t['per_decade']:+8} per decade  "
              f"(p={t['p_value']}, {verdict})")
    print("\nReminder: 17 years is short for climate; ENSO swings dominate. A "
          "non-significant slope does not contradict the 40-yr official record.")


def make_figure(yearly: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    for ax, (col, label) in zip(axes.flat, METRICS.items()):
        m = yearly[col].notna()
        yrs, vals = yearly["year"][m], yearly[col][m]
        ax.plot(yrs, vals, "o-", color="#2c7fb8", lw=1.5, ms=4)
        # trend line
        res = stats.linregress(yrs, vals)
        ax.plot(yrs, res.intercept + res.slope * yrs,
                "--", color="#d95f0e", lw=1.5,
                label=f"trend (p={res.pvalue:.2f})")
        ax.set_title(label, fontsize=10)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
    fig.suptitle("Singapore rainfall trends, 2009–2025 (17 yrs — short, ENSO-dominated)",
                 fontsize=12)
    fig.tight_layout()
    FIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_PATH, dpi=130)
    plt.close(fig)


def main() -> None:
    daily = load_history()
    yearly = yearly_island_metrics(daily)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    yearly.to_csv(OUT_CSV, index=False)
    make_figure(yearly)

    report(yearly)
    print(f"\nSaved {OUT_CSV}")
    print(f"Saved {FIG_PATH}")


if __name__ == "__main__":
    main()
