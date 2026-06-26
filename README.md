# Singapore Disaster Risk Mapping

A data-driven project aiming to find out environmental hazards that actually affect Singapore.
It is grounded in real, open data, and honest about which risks are present-day
versus low-probability risks.

## Why I built this

I recall seeing the claim that Singapore, which is long considered safe from natural disasters, might now face hazards that were "previously impossible," like earthquakes. As a
data science and economics student interested in the environment, I wanted to check
whether the data actually supported that.

It mostly didn't, and that turned out to be the interesting part:

- **Earthquakes aren't the story.** Singapore sits on the stable Sunda Block, not a
  plate boundary, so it doesn't generate its own earthquakes. It only *feels* distant
  tremors from the Sunda Megathrust off Sumatra. Climate change wouldn't change this.
- **The real, escalating, climate-driven threat is the sea.** About 30% of Singapore is
  less than 5m above mean sea level. The government's [Third National Climate Change
  Study (2024)](https://www.nccs.gov.sg/singapores-climate-action/coastal-protection/)
  projects mean sea-level rise of up to **1.15m by 2100** and **~2m by 2150**, which
  combined with storm surge and high tide could push water levels to **4–5m**. In
  2019, the government committed [**S$100 billion or more**](https://www.straitstimes.com/singapore/environment/singapore-could-spend-100-billion-or-more-over-100-years-to-tackle-threat-of)
  over 50–100 years to coastal defence, and has since passed a Coastal Protection Bill
  and [launched the "Long Island" reclamation project](https://www.nccs.gov.sg/singapores-climate-action/coastal-protection/).
- **Flash flooding is the hazard already happening, and the rain is intensifying.**
  Since 2010, Singapore has seen recurring flash floods (e.g. the 2010 Orchard Road
  event) when intense tropical rainfall meets low-lying, heavily paved terrain. Singapore's [annual rainfall has risen ~83 mm per decade since 1980](https://www.nccs.gov.sg/singapores-climate-action/impact-of-climate-change-in-singapore/),
  and the Third National Climate Change Study projects **extreme rainfall increasing
  across all seasons** (by as much as 92% in the inter-monsoon months). Heavier
  downpours on the same paved, low-lying terrain, with rising seas straining coastal
  drainage, means the flood problem compounds.
- **Tsunami is a low-probability risk.** A [2024 NTU Earth Observatory
  study](https://mothership.sg/2024/07/singapore-tsunami-risk/) found that an undersea
  volcanic eruption in the Andaman Sea could send a tsunami to Singapore through the
  Malacca Strait.

Therefore, this project is really an exercise in **data literacy**. I aim to take popular but
slightly inaccurate (clickbaity) headlines and replace them with what the evidence supports: that
Singapore's defining environmental risk is **water** (rising seas + intense rainfall),
not earthquakes.

## What it does (planned)

| Layer | Hazard | Approach |
|-------|--------|----------|
| Sea-level-rise inundation | Coastal flooding | Map which low-lying areas flood under the official SLR scenarios (+1 m, +2 m, +5 m surge) using elevation data |
| Flood risk index | Flash flooding | Rainfall intensity × terrain (elevation, drainage, imperviousness), validated against PUB's known flood-prone areas |
| Economic exposure | Both | Population, land use and property value sitting inside the inundation zones: a back-of-envelope cost vs. the S$100 B coastal-defence commitment |
| Tail-risk layer | Tsunami / seismic | USGS Sunda-shelf seismic history + the 2024 tsunami finding, shown as low-probability context |
| Dashboard | All | Interactive Folium / Streamlit map with per-planning-area risk scores |

## Data sources (all open)

- **Rainfall**: [data.gov.sg real-time API](https://data.gov.sg) (NEA rain gauges)
- **Elevation**: SRTM / OpenTopoData (low-lying zone identification)
- **Sea-level-rise scenarios**: NCCS Third National Climate Change Study (2024)
- **Flood-prone areas**: PUB / data.gov.sg
- **Seismic events**: USGS Earthquake API
- **Land use & population**: data.gov.sg / SingStat (for economic exposure)

## Setup

```bash
pip install -r requirements.txt
python -m src.data.fetch_rainfall   # pull a live rainfall snapshot
```

## Stack

Python ; pandas ; GeoPandas ; rasterio ; XGBoost ; SHAP ;
statsmodels ; Folium ; Streamlit
