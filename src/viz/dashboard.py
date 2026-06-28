"""Combined interactive dashboard: all hazard layers on one map.

Builds a single Folium map with toggleable layers, which are: coastal sea-level-rise
exposure, flash-flood rainfall exposure, residents exposed, and the regional
earthquake tail-risk. Then, the map writes it to docs/index.html so it can be served
directly by GitHub Pages.

    python -m src.viz.dashboard

Output:
    docs/index.html
"""

from __future__ import annotations

from pathlib import Path

import branca.colormap as cm
import folium
import geopandas as gpd
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
PROC = REPO_ROOT / "data" / "processed"
BOUNDARIES = REPO_ROOT / "data" / "raw" / "boundaries" / "planning_areas.geojson"
QUAKES = REPO_ROOT / "data" / "raw" / "seismic" / "earthquakes.csv"
OUT_PATH = REPO_ROOT / "docs" / "index.html"

SG_CENTER = (1.3521, 103.8198)


def choropleth_layer(fmap, gdf, column, name, caption, palette, show, tooltip_fields, tooltip_aliases):
    """Add one toggleable choropleth layer coloured by `column`."""
    valid = gdf[column].dropna()
    colormap = palette.scale(float(valid.min()), float(valid.max()))
    colormap.caption = caption

    fg = folium.FeatureGroup(name=name, show=show)
    folium.GeoJson(
        gdf,
        style_function=lambda f, col=column, cmap=colormap: {
            "fillColor": "#cccccc" if f["properties"].get(col) is None else cmap(f["properties"][col]),
            "color": "white", "weight": 0.5, "fillOpacity": 0.75,
        },
        highlight_function=lambda _f: {"weight": 2, "color": "#333"},
        tooltip=folium.GeoJsonTooltip(fields=tooltip_fields, aliases=tooltip_aliases, localize=True),
    ).add_to(fg)
    fg.add_to(fmap)
    colormap.add_to(fmap)


def quake_layer(fmap):
    """Add regional earthquakes (M>=6) as a toggleable tail-risk layer."""
    df = pd.read_csv(QUAKES)
    df = df[df["magnitude"] >= 6]
    fg = folium.FeatureGroup(name="Tail-risk: earthquakes M≥6 (1960–2025)", show=False)
    for _, q in df.iterrows():
        folium.CircleMarker(
            location=(q["latitude"], q["longitude"]),
            radius=(q["magnitude"] - 4) ** 1.6,
            color="#b30000", fill=True, fill_opacity=0.4, weight=0.5,
            popup=f"M{q['magnitude']} — {q['place']}<br>{q['distance_to_sg_km']:.0f} km from SG",
        ).add_to(fg)
    fg.add_to(fmap)


def main() -> None:
    boundaries = gpd.read_file(BOUNDARIES).assign(
        planning_area=lambda g: g["PLN_AREA_N"].str.title()
    )
    slr = gpd.read_file(PROC / "slr_scenarios_by_area.geojson")
    susc = gpd.read_file(PROC / "coastal_susceptibility_by_area.geojson")
    exposure = boundaries.merge(pd.read_csv(PROC / "economic_exposure_by_area.csv"),
                                on="planning_area", how="left")

    # tiles=None so Folium doesn't auto-add the basemap as a toggle named
    # "cartodbpositron"; add it ourselves with control=False to keep it out
    # of the layer control (it's the background, not a hazard layer).
    fmap = folium.Map(location=SG_CENTER, zoom_start=11, tiles=None)
    folium.TileLayer("CartoDB positron", name="Base map", control=False).add_to(fmap)

    choropleth_layer(
        fmap, slr, "pct_y2150_2m", "Coastal: % land flooded at +2 m (≈2150)",
        "% of land ≤ 2 m", cm.linear.Blues_09, show=True,
        tooltip_fields=["planning_area", "pct_y2100_1m", "pct_y2150_2m", "pct_worstcase_4m"],
        tooltip_aliases=["Area", "% flooded +1 m", "% flooded +2 m", "% flooded +4 m"],
    )
    choropleth_layer(
        fmap, susc, "heavy_days_per_year", "Flash: heavy-rain days/yr (nearest gauge)",
        "Heavy-rain days/yr (≥50 mm)", cm.linear.YlGnBu_09, show=False,
        tooltip_fields=["planning_area", "heavy_days_per_year", "nearest_gauge"],
        tooltip_aliases=["Area", "Heavy-rain days/yr", "Nearest gauge"],
    )
    choropleth_layer(
        fmap, exposure, "exposed_2150_2m", "Exposure: residents flooded at +2 m",
        "Residents in +2 m flood zone", cm.linear.OrRd_09, show=False,
        tooltip_fields=["planning_area", "population", "exposed_2150_2m"],
        tooltip_aliases=["Area", "Residents", "Residents exposed +2 m"],
    )
    quake_layer(fmap)

    folium.LayerControl(collapsed=False).add_to(fmap)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fmap.save(str(OUT_PATH))
    print(f"Saved dashboard to {OUT_PATH}")
    print("To host: push, then GitHub repo Settings -> Pages -> Deploy from branch -> /docs")


if __name__ == "__main__":
    main()
