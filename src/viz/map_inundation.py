"""Render the sea-level-rise inundation layer as an interactive choropleth map.

Takes data/processed/inundation_by_area.geojson (planning-area polygons with the
low-lying stats already joined on) and colours each area by the share of its land
sampled at or below 2m elevation. This is the clearest single proxy for sea-level-rise
exposure. Hovering an area shows the full breakdown.

    python -m src.viz.map_inundation

Output:
    outputs/inundation_map.html   (open in any browser)
"""

from __future__ import annotations

from pathlib import Path

import branca.colormap as cm
import folium
import geopandas as gpd

REPO_ROOT = Path(__file__).resolve().parents[2]
INUNDATION = REPO_ROOT / "data" / "processed" / "inundation_by_area.geojson"
OUT_PATH = REPO_ROOT / "outputs" / "inundation_map.html"

SG_CENTER = (1.3521, 103.8198)
COLOR_FIELD = "pct_below_2m"
NO_DATA_COLOR = "#cccccc"


def build_map(gdf: gpd.GeoDataFrame) -> folium.Map:
    """Build a Folium choropleth coloured by % of land at or below 2 m."""
    vmax = float(gdf[COLOR_FIELD].max())
    colormap = cm.linear.YlOrRd_09.scale(0, vmax)
    colormap.caption = "Share of land area at or below 2 m elevation (%)"

    def style(feature: dict) -> dict:
        value = feature["properties"].get(COLOR_FIELD)
        return {
            "fillColor": NO_DATA_COLOR if value is None else colormap(value),
            "color": "white",
            "weight": 0.6,
            "fillOpacity": 0.75,
        }

    fmap = folium.Map(location=SG_CENTER, zoom_start=11, tiles="CartoDB positron")

    folium.GeoJson(
        gdf,
        style_function=style,
        highlight_function=lambda _f: {"weight": 2, "color": "#333333"},
        tooltip=folium.GeoJsonTooltip(
            fields=[
                "planning_area",
                "pct_below_1m", "pct_below_2m", "pct_below_5m",
                "elev_median_m", "n_land_points",
            ],
            aliases=[
                "Planning area",
                "% land ≤ 1 m", "% land ≤ 2 m", "% land ≤ 5 m",
                "Median elevation (m)", "Sample points",
            ],
            localize=True,
        ),
        name="Inundation by planning area",
    ).add_to(fmap)

    colormap.add_to(fmap)
    folium.LayerControl().add_to(fmap)
    return fmap


def main() -> None:
    gdf = gpd.read_file(INUNDATION)
    fmap = build_map(gdf)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fmap.save(str(OUT_PATH))

    n_with_data = gdf[COLOR_FIELD].notna().sum()
    print(f"Mapped {n_with_data}/{len(gdf)} planning areas.")
    print(f"Saved interactive map to {OUT_PATH}")
    print("Open it in a browser to explore (hover an area for the breakdown).")


if __name__ == "__main__":
    main()
