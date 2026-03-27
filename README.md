# 🐟 Polysim — Policy Simulation Engine

> Every policy is a bet on how 5.6 million people will react.
> Polysim lets you run that bet 1,000 times before anyone votes.

## What it does

Upload a Singapore government policy document → Polysim spawns 40 autonomous LLM agents representing real demographic micro-segments → Watch sentiment and vote predictions emerge across GRC constituencies in real-time, with social contagion cascades.

## Architecture

```
Policy PDF → OpenAI (parse provisions) → Agent Engine (40 personas × GPT-4o)
                                                    ↓
TinyFish (real-time SG sentiment scraping) → Contagion Model → Dashboard
```

- **TinyFish** scrapes real Singapore demographic data + public sentiment
- **OpenAI GPT-4o** powers agent reasoning (40 representative personas × population weights)
- **Social contagion model** propagates sentiment through demographic networks
- **Interactive levers** let you adjust policy parameters and see outcomes shift live
- **react-leaflet choropleth map** of Singapore GRC boundaries

## Quick Start

```bash
cp .env.example .env     # Add your OPENAI_API_KEY and TINYFISH_API_KEY
chmod +x demo.sh
./demo.sh
```

Then open http://localhost:3000, upload a policy PDF, and click **Run Simulation**.

## Stack

| Layer | Tech |
|-------|------|
| Frontend | React 18 + Vite + Tailwind CSS + react-leaflet + recharts |
| Backend | Python FastAPI + WebSocket streaming |
| LLM | OpenAI gpt-4o (agent reasoning + PDF parsing) |
| Scraping | TinyFish API |
| Data | Singapore Census 2020 + Electoral Boundaries (data.gov.sg) |

## Data Sources

- Electoral boundaries: [data.gov.sg ELD dataset](https://data.gov.sg/datasets/d_6077aa5ab73d447b32f451ea224221b6/view)
- Demographics: Singapore Census 2020 (SingStat)
- GE2020 results: [data.gov.sg ELD](https://data.gov.sg/datasets/d_581a30bee57fa7d8383d6bc94739ad00/view)

## Setup Notes

1. **GeoJSON**: Place `sg_electoral_boundaries.geojson` in `frontend/public/`
2. **TinyFish**: Update `backend/scraper.py` with actual API endpoint after workshop
3. **Sample PDF**: Put a SG policy document in `data/sample_policy.pdf`

## Built at TinyFish × OpenAI Hackathon 2026 — NUS Acacia
