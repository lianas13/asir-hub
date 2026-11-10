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


class NoRedirects(urllib.request.HTTPRedirectHandler):
    """Inspect Apps Script's temporary redirect before retrieving its JSON."""
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def _get_json_google(url):
    """Follow only Google's HTTPS hosts, retrying transient ContentService 404s."""
    opener = urllib.request.build_opener(NoRedirects())
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ASIR-HUB/1.0)",
        "Accept": "application/json, text/plain, */*",
    }
    current = url
    for redirect_number in range(6):
        parsed = urllib.parse.urlparse(current)
        if parsed.scheme != "https" or parsed.hostname not in (
                "script.google.com", "script.googleusercontent.com"):
            raise ValueError("Redirección fuera de los servidores autorizados de Google")

        for echo_try in range(3):
            request = urllib.request.Request(current, headers=headers)
            try:
                with opener.open(request, timeout=40) as response:
                    raw = response.read(2_000_001)
                    if len(raw) > 2_000_000:
                        raise ValueError("La respuesta de Google supera el límite de tamaño")
                    if not raw.lstrip().startswith(b"{"):
                        raise RuntimeError("Google respondió con una página HTML en vez de JSON")
                    return json.loads(raw)
            except urllib.error.HTTPError as exc:
                if exc.code in (301, 302, 303, 307, 308):
                    location = exc.headers.get("Location")
                    if not location:
                        raise RuntimeError("Google redirige sin indicar destino") from None
                    current = urllib.parse.urljoin(current, location)
                    next_host = urllib.parse.urlparse(current).hostname
                    if next_host not in ("script.google.com", "script.googleusercontent.com"):
                        raise ValueError("Redirección a un dominio no permitido") from None
                    break
                # Google Apps Script ContentService returns a one-time URL.
                # Its content may not be ready at the time of the redirect.
                if exc.code == 404 and parsed.hostname == "script.googleusercontent.com" and echo_try < 2:
                    print(f"Google ContentService todavía no ha servido el JSON; reintento {echo_try + 1}/2")
                    time.sleep(3)
                    continue
                raise RuntimeError(
                    "HTTP " + str(exc.code) + " en " +
                    ("la redirección temporal de Google" if parsed.hostname == "script.googleusercontent.com"
                     else "el enlace principal de Apps Script")
                ) from None
        else:
            raise RuntimeError("No se ha podido recuperar el contenido temporal de Google")
    raise RuntimeError("Google ha generado demasiadas redirecciones")


def get_feed(url):
    # Aceptamos enlaces de implementación (/exec) y redirigidos, pero nunca
    # imprimimos rutas, parámetros, tokens ni valores privados.
    url = url.strip().strip('"').strip("'").strip()
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in (
            "script.google.com", "script.googleusercontent.com"):
        raise ValueError("El enlace debe ser HTTPS de Google Apps Script")
    if not parsed.path or parsed.path == "/":
        raise ValueError("El enlace no contiene la dirección de la aplicación web")
    if parsed.hostname == "script.googleusercontent.com":
        print("Diagnóstico seguro: URL de redirección temporal de Google, no enlace original /exec.")
    else:
        # Google a veces añade el índice de cuenta /u/0 a la dirección,
        # que funciona en el navegador pero puede fallar sin sesión.
        path = parsed.path
        indexed = re.fullmatch(r"/macros/u/[0-9]+/s/([^/]+)/exec", path)
        if indexed:
            clean_path = "/macros/s/" + indexed.group(1) + "/exec"
            url = urllib.parse.urlunparse(parsed._replace(path=clean_path))
            print("Diagnóstico seguro: URL con índice de cuenta, normalizada a /macros/s/.../exec")
        elif re.fullmatch(r"/macros/s/[^/]+/exec", path):
            print("Diagnóstico seguro: URL canónica /macros/s/.../exec")
        elif re.fullmatch(r"/a/macros/[^/]+/s/[^/]+/exec", path):
            print("Diagnóstico seguro: URL Workspace /a/macros/.../exec")
        elif path.endswith("/dev"):
            print("Diagnóstico seguro: URL de desarrollo /dev. Necesitas la implementación /exec.")
        else:
            # Distintas cuentas de Google pueden anteponer rutas adicionales.
            # Si hay un ID de implementación reconocible al final, recuperamos
            # su URL canónica sin revelar el ID ni los parámetros privados.
            deployment = re.search(r"/s/([A-Za-z0-9_-]{20,})/exec/?$", path)
            if deployment:
                normalized = "/macros/s/" + deployment.group(1) + "/exec"
                url = urllib.parse.urlunparse(parsed._replace(path=normalized))
                print("Diagnóstico seguro: ruta con prefijos de cuenta normalizada a /macros/s/.../exec")
            else:
                print("Diagnóstico seguro: la URL de GitHub NO tiene un identificador de implementación /s/ID/exec reconocible.")
                print("Solución: copiar la URL de Implementar > Gestionar implementaciones, añadir ?key=CLAVE y actualizar GOOGLE_EVENTS_URL.")

    for attempt in range(4):
        try:
            data = _get_json_google(url)
            if not isinstance(data, dict) or data.get("status") != "ready":
                raise ValueError("Google no autoriza la lectura (comprueba la implementación y la clave)")
            if not isinstance(data.get("events"), list):
                raise ValueError("Google no ha devuelto una lista de eventos")
            return data
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
            if isinstance(exc, RuntimeError):
                detail = str(exc)
            elif isinstance(exc, json.JSONDecodeError):
                detail = "Google ha devuelto un JSON mal formado"
            else:
                detail = "Fallo de red al consultar Google"
            if attempt == 3:
                raise RuntimeError(detail) from None
            print(f"Conexión a Google no disponible ({detail}). Nueva consulta {attempt + 2}/4")
            time.sleep(3 * (attempt + 1))
    raise RuntimeError("No se han podido consultar los eventos de Google")


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
            "all_day": all_day, "type": ("examen" if item.get("source") == "manual" and item.get("type") == "examen" else event_type(title))
        })
    return sorted({e["id"]: e for e in normalized}.values(), key=lambda e: e["start"])


def main():
    url = os.environ.get("GOOGLE_EVENTS_URL", "").strip()
    if not url:
        print("No se ha configurado GOOGLE_EVENTS_URL. Publicando la web sin eventos.")
        payload = {"status": "config", "updated_at": None, "events": []}
    else:
        fetched = get_feed(url)
        events = normalize(fetched["events"])
        print(f"Leídos {len(events)} eventos académicos desde Google Calendar.")
        payload = {
            "status": "ready",
            "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "events": events,
            "manual_enabled": fetched.get("manual_enabled") is True,
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
