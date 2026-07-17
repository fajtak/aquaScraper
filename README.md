# AquaScraper

Real-time dashboard for Aquacentrum Pardubice occupancy and water temperatures.

Scrapes [aquapce.cz](https://www.aquapce.cz) every 2 minutes (05:50–21:10 CET), stores data in SQLite, serves via FastAPI + Chart.js. 

## Quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8069
```

Open http://localhost:8069

## API

| Endpoint | Description |
|---|---|
| `GET /api/readings/days?days=7` | Data grouped by day, time as minutes since midnight |
| `GET /api/readings?limit=500` | Raw readings chronologically |
| `GET /api/events` | SSE – event `new_data` on each scrape |

## Stack

FastAPI, SQLite (aiosqlite), Chart.js 4, httpx + BeautifulSoup.
