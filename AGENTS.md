# AquaScraper

Real-time dashboard scrapující obsazenost a teploty z aquapce.cz. FastAPI + SQLite + Chart.js.

## Run

```bash
.venv/bin/uvicorn app.main:app --reload --port 8069
# pak http://localhost:8069
```

## Scraper

- Běží každých **120 s**, ale **jen 5:50–21:10** pražského času (`_is_open()`).
- Cíl: `https://www.aquapce.cz`, parsuje `ul.table > li` – pokud se změní HTML struktura, scraper tiše vrátí `None`.
- Timestampy se ukládají v **UTC**, převod do Prague timezone až v `api_readings_days`.

## API

- `GET /api/readings/days?days=7` – **primární endpoint frontendu**. Vrací data předgroupovaná po dnech, čas jako minuty od půlnoci (`t: 396` = 06:36). Každý záznam: `{t, bazen, aqua, letni_areal, wellness, rekreaeni_temp, brouzdaliste_temp}`.
- `GET /api/readings?limit=N` – syrová data, chronologicky.
- `GET /api/events` – SSE, event `new_data`. Fallback na 30s polling při chybě.
- Žádné auth, rate limiting, env vars ani konfigurace.

## Frontend (static/index.html)

- **Chart.js 4 + chartjs-plugin-zoom** z CDN (ne npm). Plugin se registruje přes UMD globál `ChartZoom`.
- X-osa: `type: "linear"`, rozsah **360–1320** (minuty = 06:00–22:00), ticky formátované na `HH:mm`.
- Data se mapují jako `{x: r.t, y: r[m.key]}` (`parsing: false`).
- Tooltip: `filter: (item, idx) => idx === 0`, `label` callback sbírá nejbližší body ze všech datasetů (tolerance 3 min) a řadí od nejstaršího data.
- Zoom/pan jen na ose Y.

## Databáze

- SQLite v `data/aqua.db`, vytvoří se automaticky. Schema: `readings(id, timestamp, bazen, aqua, letni_areal, wellness, rekreaeni_temp, brouzdaliste_temp)`.
- Index na `timestamp`.

## Další

- **Žádné testy**, žádný CI/CD, není to git repozitář.
- Python 3.11.4, venv v `.venv/`.
- HTML se servíruje z `app/static/index.html` přes `/` endpoint. Static mount na `/static` je nevyužitý.
- Pokud budeš upravovat frontend, ověř, že `ChartZoom` je zaregistrovaný a že tooltip `filter` nekoliduje s novými callbacky.
