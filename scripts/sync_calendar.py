#!/usr/bin/env python3
"""Leer eventos de Aules sin publicar URL privada, descripciones ni identificadores."""
import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from icalendar import Calendar

ZONE = ZoneInfo("Europe/Madrid")
OUTPUT = Path(__file__).resolve().parents[1] / "site" / "events.json"
EXAM = re.compile(r"ex[aá]men|exam\b|prueba\s+(?:escrita|final)|control\b|parcial\b", re.I)
TASK = re.compile(r"tarea|entrega|actividad|pr[aá]ctica|assignment|due\b|vencimiento|deberes|trabajo", re.I)

def safe_title(value):
    return re.sub(r"\s+", " ", re.sub(r"[\x00-\x1f\x7f]", " ", str(value or ""))).strip()[:180]

def event_kind(title):
    return "examen" if EXAM.search(title) else "entrega" if TASK.search(title) else "otro"

def read_events(raw):
    cal = Calendar.from_ical(raw)
    today = datetime.now(ZONE).date()
    events = []
    allow = [x.strip().casefold() for x in os.environ.get("AULES_TITLE_ALLOWLIST", "").split("||") if x.strip()]
    for item in cal.walk("VEVENT"):
        title = safe_title(item.get("SUMMARY", ""))
        dt = item.get("DTSTART")
        if not title or dt is None or (allow and not any(term in title.casefold() for term in allow)):
            continue
        start = dt.dt
        if not isinstance(start, (date, datetime)):
            continue
        local_day = start.astimezone(ZONE).date() if isinstance(start, datetime) and start.tzinfo else (start.date() if isinstance(start, datetime) else start)
        if not (today - timedelta(days=60) <= local_day <= today + timedelta(days=370)):
            continue
        all_day = not isinstance(start, datetime)
        if not all_day:
            if start.tzinfo is None:
                start = start.replace(tzinfo=ZONE)
            start_str = start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        else:
            start_str = start.isoformat()
        identifier = hashlib.sha256((title + "|" + start_str).encode()).hexdigest()[:16]
        events.append({"id": identifier, "title": title, "start": start_str, "all_day": all_day, "type": event_kind(title)})
    return sorted({e["id"]: e for e in events}.values(), key=lambda e: e["start"])

def main():
    url = os.environ.get("AULES_ICS_URL", "").strip()
    if not url:
        payload = {"status": "config", "updated_at": None, "events": []}
        print("Falta configurar AULES_ICS_URL: se mostrará un calendario vacío.")
    else:
        if not url.startswith("https://"):
            raise ValueError("AULES_ICS_URL debe usar HTTPS")
        request = urllib.request.Request(url, headers={"User-Agent": "ASIR-HUB/1.0", "Accept": "text/calendar"})
        with urllib.request.urlopen(request, timeout=25) as response:
            if not response.geturl().startswith("https://"):
                raise ValueError("Redirección insegura")
            raw = response.read(5_000_001)
        if len(raw) > 5_000_000 or b"BEGIN:VCALENDAR" not in raw[:1000]:
            raise ValueError("La respuesta no parece un calendario ICS válido de menos de 5 MB")
        events = read_events(raw)
        payload = {"status": "ready", "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "events": events}
        print(f"Importados {len(events)} eventos.")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error al importar Aules ({type(exc).__name__}). Comprueba el secret y la exportación ICS.", file=sys.stderr)
        sys.exit(1)
