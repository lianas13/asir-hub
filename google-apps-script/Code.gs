/**
 * ASIR HUB · Puente de solo lectura con Google Calendar.
 * No consulta Aules directamente, ni publica credenciales de Aules o Google.
 *
 * Configuración en Ajustes del proyecto > Propiedades del script:
 *   ASIR_CALENDAR_ID: ID exacto del calendario suscrito desde Aules
 *   ASIR_FEED_KEY: se crea ejecutando crearClave() una vez
 */

const HUSO = "Europe/Madrid";

function listarCalendarios() {
  const calendars = CalendarApp.getAllCalendars();
  calendars.forEach(calendar => {
    console.log(calendar.getName() + " | ID: " + calendar.getId());
  });
}

function crearClave() {
  const props = PropertiesService.getScriptProperties();
  if (!props.getProperty("ASIR_FEED_KEY")) {
    props.setProperty("ASIR_FEED_KEY", Utilities.getUuid().replace(/-/g, "") + Utilities.getUuid().replace(/-/g, ""));
  }
  console.log("Clave privada creada. No la copies en el código público.");
}

function mostrarEnlacePrivado() {
  const props = PropertiesService.getScriptProperties();
  const key = props.getProperty("ASIR_FEED_KEY");
  const url = ScriptApp.getService().getUrl();
  if (!key) throw new Error("Ejecuta primero crearClave().");
  if (!url) throw new Error("Primero despliega como aplicación web.");
  console.log(url + (url.indexOf("?") >= 0 ? "&" : "?") + "key=" + encodeURIComponent(key));
}

function responder(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function doGet(e) {
  const props = PropertiesService.getScriptProperties();
  const expected = props.getProperty("ASIR_FEED_KEY");
  const provided = e && e.parameter && e.parameter.key;
  if (!expected || !provided || provided !== expected) {
    return responder({status: "error", error: "No autorizado"});
  }

  const calendarId = props.getProperty("ASIR_CALENDAR_ID");
  if (!calendarId) return responder({status: "error", error: "Falta ASIR_CALENDAR_ID"});
  try {
    const cal = CalendarApp.getCalendarById(calendarId);
    if (!cal) return responder({status: "error", error: "Calendario no encontrado o sin acceso"});
    if (cal.isMyPrimaryCalendar()) {
      return responder({status: "error", error: "No se permite publicar el calendario principal"});
    }
    const now = new Date();
    const begin = new Date(now.getTime() - 60 * 86400000);
    const end = new Date(now.getTime() + 370 * 86400000);
    const calendarEvents = cal.getEvents(begin, end);

    const events = calendarEvents.slice(0, 1000).map(event => {
      const allDay = event.isAllDayEvent();
      const start = allDay
        ? Utilities.formatDate(event.getAllDayStartDate(), HUSO, "yyyy-MM-dd")
        : event.getStartTime().toISOString();
      return {
        title: String(event.getTitle() || "").replace(/[\u0000-\u001f\u007f]/g, " ").trim().slice(0, 180),
        start: start,
        all_day: allDay
      };
    }).filter(event => event.title.length > 0);

    return responder({status: "ready", events: events});
  } catch (error) {
    console.error("ASIR HUB: error al leer el calendario: " + error);
    return responder({status: "error", error: "No se pudieron leer los eventos"});
  }
}
