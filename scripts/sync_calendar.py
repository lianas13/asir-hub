#!/usr/bin/env python3
"""ASIR HUB: copia únicamente títulos y fechas del calendario Google autorizado.

La URL privada de Apps Script se lee de GOOGLE_EVENTS_URL y no se registra.
No se publican descripciones, URLs, correos ni identificadores de Google.
"""
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ZONE = ZoneInfo("Europe/Madrid")
OUTPUT = Path(__file__).resolve().parents[1] / "site" / "events.json"
EXAM = re.compile(r"ex[aá]men|exam\b|prueba\s+(?:escrita|final)|control\b|parcial\b", re.I)
TASK = re.compile(r"tarea|entrega|actividad|pr[aá]ctica|assignment|due\b|vencimiento|deberes|trabajo", re.I)


def event_type(title):
    return "examen" if EXAM.search(title) else "entrega" if TASK.search(title) else "otro"


def get_feed(url):
    # Algunas personas copian la URL que el navegador muestra después de una
    # redirección de Apps Script (script.googleusercontent.com/macros/echo).
    # También puede existir la variante /a/macros/ para Google Workspace.
    # No imprimimos nunca query strings ni tokens.
    url = url.strip().strip('"').strip("'").strip()
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in (
            "script.google.com", "script.googleusercontent.com"):
        raise ValueError(
            "El secreto debe contener un enlace HTTPS de Google Apps Script"
        )
    canonical = parsed.hostname == "script.google.com" and (
        re.fullmatch(r"/macros/s/[^/]+/exec", parsed.path) is not None
        or re.fullmatch(r"/a/macros/[^/]+/s/[^/]+/exec", parsed.path) is not None
    )
    redirected = (
        parsed.hostname == "script.googleusercontent.com"
        and parsed.path == "/macros/echo"
    )
    if not (canonical or redirected):
        raise ValueError(
            "Ruta de Google no reconocida: utiliza la URL de despliegue terminada en /exec?key=..."
        )
    if not parsed.query:
        raise ValueError(
            "La URL no tiene parámetros privados; copia el enlace completo generado por mostrarEnlacePrivado"
        )
    if redirected:
        print(
            "Aviso: se está usando el enlace redirigido de Google; "
            "puede caducar. Para uso permanente, guarda la URL original "
            "de script.google.com terminada en /exec?key=..."
        )

    request = urllib.request.Request(url, headers={
        "User-Agent": "ASIR-HUB/1.0",
        "Accept": "application/json",
    })
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=40) as response:
                final_host = urllib.parse.urlparse(response.geturl()).hostname
                if final_host not in ("script.google.com", "script.googleusercontent.com"):
                    raise ValueError("Redirección fuera de los servidores de Google")
                raw = response.read(2_000_001)
                if len(raw) > 2_000_000:
                    raise ValueError("Respuesta demasiado grande")
            data = json.loads(raw)
            if not isinstance(data, dict) or data.get("status") != "ready":
                raise ValueError("Google no ha autorizado la lectura del calendario")
            if not isinstance(data.get("events"), list):
                raise ValueError("La respuesta no contiene una lista de eventos")
            return data["events"]
        except urllib.error.HTTPError as exc:
            if exc.code not in (404, 408, 429, 500, 502, 503, 504) or attempt == 2:
                raise RuntimeError(f"Google ha devuelto HTTP {exc.code}") from None
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == 2:
                raise RuntimeError("No se pudo establecer conexión con Google") from None
        except json.JSONDecodeError:
            if attempt == 2:
                raise RuntimeError("Google devolvió una respuesta que no es JSON") from None
        print(f"Reintentando lectura de Google Calendar ({attempt + 2}/3).")
        time.sleep(2 * (attempt + 1))
    raise RuntimeError("Error de conexión")


def normalize(events):
    today = datetime.now(ZONE).date()
    normalized = []
    for item in events[:1500]:
        if not isinstance(item, dict):
            continue
        title = re.sub(r"[\x00-\x1f\x7f]", " ", str(item.get("title", ""))).strip()[:180]
        start = str(item.get("start", ""))
        all_day = item.get("all_day") is True
        if not title:
            continue
        try:
            if all_day:
                when = date.fromisoformat(start)
                start_out = when.isoformat()
            else:
                parsed = datetime.fromisoformat(start.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    continue
                when = parsed.astimezone(ZONE).date()
                start_out = parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        except ValueError:
            continue
        if not (today - timedelta(days=60) <= when <= today + timedelta(days=370)):
            continue
        identifier = hashlib.sha256((title + "|" + start_out).encode()).hexdigest()[:16]
        normalized.append({
            "id": identifier, "title": title, "start": start_out,
            "all_day": all_day, "type": event_type(title)
        })
    return sorted({e["id"]: e for e in normalized}.values(), key=lambda e: e["start"])


def main():
    url = os.environ.get("GOOGLE_EVENTS_URL", "").strip()
    if not url:
        print("No se ha configurado GOOGLE_EVENTS_URL. Publicando la web sin eventos.")
        payload = {"status": "config", "updated_at": None, "events": []}
    else:
        events = normalize(get_feed(url))
        print(f"Leídos {len(events)} eventos académicos desde Google Calendar.")
        payload = {
            "status": "ready",
            "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "events": events,
        }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # No mostramos jamás la URL del feed ni errores que puedan contenerla.
        msg = str(exc) if isinstance(exc, (RuntimeError, ValueError)) else type(exc).__name__
        print(f"Error seguro al leer Google Calendar: {msg}", file=sys.stderr)
        sys.exit(1)
