# Singapore Disaster Risk Mapping

A project aiming to find out environmental hazards that actually affect Singapore.
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

## What it does

Two flood hazards, treated with equal depth, plus a low-probability tail risk.

| Track | Hazard | What I do |
|-------|--------|-----------|
| **Coastal flooding** | Rising seas | Map which neighbourhoods flood as the sea rises, under Singapore's own official scenarios (+1m by 2100, +2m by 2150, ~4m with storm surge + high tide), built from elevation data |
| **Flash flooding** | Intense rain | Use 17 years of rain-gauge data (2009–2025) to map which areas get the most intense downpours, and test whether heavy rain is becoming more frequent |
| **Economic exposure** | Coastal | How many residents live inside the low-lying flood zones, set against the S$100 billion coastal-defence commitment |
| **Tail-risk context** | Tsunami / seismic | Sunda-shelf earthquake history + the 2024 tsunami study, shown as low-probability context (Singapore feels distant tremors but generates no quakes of its own) |
| **Dashboard** | All | One interactive map tying the layers together |

**Key finding so far:** a flood score built from terrain ranks Singapore's
actual flash-flood hotspots (Geylang, Bukit Timah) *low*, as those places
flood from overwhelmed **drains**, not low ground. Thus, terrain explains
**coastal** flooding well, while flash flooding is really an **infrastructure**
problem. This is why the government's response is drains and seawalls.

## Data sources (all open)

- **Rainfall (live)**: [data.gov.sg real-time API](https://data.gov.sg) (NEA rain gauges)
- **Rainfall (history + intensity)**: [weather.gov.sg daily archive](https://www.weather.gov.sg/climate-historical-daily/) — per-station daily totals and 30/60/120-min bursts, 2009–2025
- **Elevation**: SRTM / OpenTopoData (low-lying zone identification)
- **Planning-area boundaries**: data.gov.sg (URA Master Plan 2019)
- **Sea-level-rise scenarios**: NCCS Third National Climate Change Study (2024)
- **Seismic events**: USGS Earthquake API
- **Population**: data.gov.sg / SingStat (residents by planning area, for economic exposure)

## Setup

```bash
pip install -r requirements.txt
python -m src.data.fetch_rainfall   # pull a live rainfall snapshot
```

## Stack

Python ; pandas ; GeoPandas ; rasterio ; XGBoost ; SHAP ;
statsmodels ; Folium ; Streamlit
