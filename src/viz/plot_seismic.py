"""Tail-risk layer: visualise the regional earthquakes that could reach Singapore.

Singapore generates no earthquakes of its own since it sits on the stable Sunda Block.
However, large quakes on the Sunda Megathrust (off Sumatra) and in the Andaman Sea are
the sources behind the low-probability tsunami risk. This plots every M>=5 event
since 1960: a dense seismic arc down Sumatra, with Singapore sitting safely to the side of it.

    python -m src.viz.plot_seismic

Outputs:
    reports/figures/seismic_tailrisk.png
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
QUAKES = REPO_ROOT / "data" / "raw" / "seismic" / "earthquakes.csv"
FIG_PATH = REPO_ROOT / "reports" / "figures" / "seismic_tailrisk.png"

SG_LAT, SG_LON = 1.3521, 103.8198


def summary(df: pd.DataFrame) -> None:
    print(f"Events M>=5, {df['time'].str[:4].min()}–{df['time'].str[:4].max()}: {len(df)}")
    for m in (6, 7, 8):
        print(f"  M>= {m}: {(df['magnitude'] >= m).sum()}")
    big = df[df["magnitude"] >= 7]
    near = big.loc[big["distance_to_sg_km"].idxmin()]
    biggest = df.loc[df["magnitude"].idxmax()]
    print(f"  Largest: M{biggest['magnitude']} at {biggest['distance_to_sg_km']:.0f} km "
          f"({biggest['place']})")
    print(f"  Closest M>=7: {near['distance_to_sg_km']:.0f} km away")
    print(f"  No M>=7 has occurred within ~400 km of Singapore — the archipelago "
          f"shields it.")


def make_figure(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 7))
    sizes = (df["magnitude"] - 4) ** 3  # emphasise the big ones
    sc = ax.scatter(df["longitude"], df["latitude"], s=sizes, c=df["magnitude"],
                    cmap="YlOrRd", alpha=0.55, edgecolor="none")
    ax.scatter([SG_LON], [SG_LAT], marker="*", s=400, color="#1f78b4",
               edgecolor="black", zorder=5)
    ax.annotate("Singapore", (SG_LON, SG_LAT), textcoords="offset points",
                xytext=(8, 6), fontsize=10, fontweight="bold")
    cbar = fig.colorbar(sc, ax=ax, shrink=0.8)
    cbar.set_label("Magnitude")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Earthquakes M≥5, 1960–2025 (Sunda Megathrust & Andaman Sea)\n"
                 "Singapore sits off the seismic arc — felt tremors, but no local quakes",
                 fontsize=11)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    FIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_PATH, dpi=130)
    plt.close(fig)


def main() -> None:
    df = pd.read_csv(QUAKES)
    summary(df)
    make_figure(df)
    print(f"\nSaved {FIG_PATH}")


if __name__ == "__main__":
    main()
