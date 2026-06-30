import aiosqlite
from pathlib import Path
from .scraper import AquaReading

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "aqua.db"


async def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                bazen INTEGER,
                aqua INTEGER,
                letni_areal INTEGER,
                wellness INTEGER,
                rekreaeni_temp REAL,
                brouzdaliste_temp REAL
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_readings_timestamp
            ON readings(timestamp)
        """)
        await db.commit()


async def save_reading(reading: AquaReading):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO readings (timestamp, bazen, aqua, letni_areal, wellness, rekreaeni_temp, brouzdaliste_temp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reading.timestamp.isoformat(),
                reading.bazen,
                reading.aqua,
                reading.letni_areal,
                reading.wellness,
                reading.rekreaeni_temp,
                reading.brouzdaliste_temp,
            ),
        )
        await db.commit()


async def get_readings(limit: int = 500) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM readings ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in reversed(rows)]
