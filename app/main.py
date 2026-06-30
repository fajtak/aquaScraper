import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .database import init_db, save_reading, get_readings
from .scraper import fetch_and_parse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="AquaScraper")

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

_scraper_task: asyncio.Task | None = None


class EventBroadcaster:
    def __init__(self):
        self._queues: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._queues.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        self._queues.discard(q)

    async def publish(self, data: str):
        for q in list(self._queues):
            await q.put(data)


broadcaster = EventBroadcaster()


TZ_PRAGUE = ZoneInfo("Europe/Prague")
OPEN_START = time(5, 50)
OPEN_END = time(21, 10)


def _is_open() -> bool:
    now = datetime.now(TZ_PRAGUE).time()
    return OPEN_START <= now <= OPEN_END


async def _scrape_loop():
    while True:
        if not _is_open():
            await asyncio.sleep(120)
            continue

        try:
            reading = await fetch_and_parse()
            if reading:
                await save_reading(reading)
                await broadcaster.publish(json.dumps({
                    "bazen": reading.bazen,
                    "aqua": reading.aqua,
                    "letni_areal": reading.letni_areal,
                    "wellness": reading.wellness,
                    "timestamp": reading.timestamp.isoformat(),
                }))
                logger.info(
                    "Saved: bazén=%s, aqua=%s, letní areál=%s, wellness=%s",
                    reading.bazen,
                    reading.aqua,
                    reading.letni_areal,
                    reading.wellness,
                )
            else:
                logger.warning("Failed to parse page")
        except Exception as e:
            logger.error("Scrape error: %s", e)
        await asyncio.sleep(120)


@app.on_event("startup")
async def startup():
    await init_db()
    global _scraper_task
    _scraper_task = asyncio.create_task(_scrape_loop())


@app.on_event("shutdown")
async def shutdown():
    if _scraper_task:
        _scraper_task.cancel()
        try:
            await _scraper_task
        except asyncio.CancelledError:
            pass


@app.get("/api/readings")
async def api_readings(limit: int = 500):
    rows = await get_readings(limit)
    return JSONResponse(content=rows)


@app.get("/api/readings/days")
async def api_readings_days(days: int = 7):
    limit = days * 500 + 100
    rows = await get_readings(limit)
    if not rows:
        return JSONResponse(content=[])

    TZ = ZoneInfo("Europe/Prague")
    groups = defaultdict(list)
    for r in rows:
        ts = datetime.fromisoformat(r["timestamp"]).astimezone(TZ)
        date_key = ts.strftime("%Y-%m-%d")
        minutes = ts.hour * 60 + ts.minute

        groups[date_key].append({
            "t": minutes,
            "bazen": r["bazen"],
            "aqua": r["aqua"],
            "letni_areal": r["letni_areal"],
            "wellness": r["wellness"],
            "rekreaeni_temp": r["rekreaeni_temp"],
            "brouzdaliste_temp": r["brouzdaliste_temp"],
        })

    sorted_days = sorted(groups.keys(), reverse=True)[:days]
    result = [{"date": d, "readings": groups[d]} for d in sorted_days]
    return JSONResponse(content=result)


@app.get("/api/events")
async def event_stream(request: Request):
    queue = broadcaster.subscribe()

    async def generate():
        try:
            while True:
                data = await queue.get()
                yield f"event: new_data\ndata: {data}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            broadcaster.unsubscribe(queue)

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/")
async def dashboard():
    html = (STATIC_DIR / "index.html").read_text("utf-8")
    return HTMLResponse(content=html)
