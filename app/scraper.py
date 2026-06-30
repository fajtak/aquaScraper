import httpx
from bs4 import BeautifulSoup
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class AquaReading:
    timestamp: datetime
    bazen: int | None
    aqua: int | None
    letni_areal: int | None
    wellness: int | None
    rekreaeni_temp: float | None
    brouzdaliste_temp: float | None


def _parse_int(text: str) -> int | None:
    cleaned = text.strip()
    try:
        return int(cleaned)
    except (ValueError, TypeError):
        return None


def _parse_float(text: str) -> float | None:
    cleaned = text.strip()
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def parse_html(html: str) -> AquaReading | None:
    soup = BeautifulSoup(html, "html.parser")
    table_items = soup.select("ul.table > li")
    if not table_items:
        return None

    bazen = aqua = letni_areal = wellness = None
    rekreaeni_temp = brouzdaliste_temp = None

    for li in table_items:
        text = li.get_text(" ", strip=True)
        is_temp = "Teploty" in text

        if is_temp:
            sub_lis = li.select("ul li")
            for sub in sub_lis:
                sub_text = sub.get_text(" ", strip=True)
                span = sub.find("span")
                if not span:
                    continue
                val = _parse_float(span.get_text())
                if "rekreační" in sub_text:
                    rekreaeni_temp = val
                elif "brouzdaliště" in sub_text:
                    brouzdaliste_temp = val
        elif text.startswith("bazén"):
            span = li.find("span")
            if span:
                bazen = _parse_int(span.get_text())
        elif text.startswith("aqua"):
            span = li.find("span")
            if span:
                aqua = _parse_int(span.get_text())
        elif "Letní areál" in text:
            span = li.find("span")
            if span:
                letni_areal = _parse_int(span.get_text())
        elif text.startswith("wellness"):
            span = li.find("span")
            if span:
                wellness = _parse_int(span.get_text())

    return AquaReading(
        timestamp=datetime.now(timezone.utc),
        bazen=bazen,
        aqua=aqua,
        letni_areal=letni_areal,
        wellness=wellness,
        rekreaeni_temp=rekreaeni_temp,
        brouzdaliste_temp=brouzdaliste_temp,
    )


async def fetch_and_parse() -> AquaReading | None:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get("https://www.aquapce.cz")
        resp.raise_for_status()
        return parse_html(resp.text)
