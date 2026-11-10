# ASIR HUB

Web responsive de calendario, exámenes y entregas de clase. Usa **Aules → Google Calendar → Google Apps Script → GitHub Actions → GitHub Pages**.

La web de GitHub Pages es pública. **El calendario de Google que selecciones debe contener únicamente eventos que puedas compartir con la clase.** El programa publica los títulos y las fechas de ese calendario; no publica correos, descripciones, enlaces a Aules o identificadores privados.

## 1. Encontrar el calendario Aules en Google

Ya debes haber añadido el calendario de Aules mediante **Google Calendar → Otros calendarios → + → Desde URL** y haber comprobado que aparecen sus eventos.

## 2. Crear el puente privado en Google Apps Script

1. Abre [script.google.com](https://script.google.com/home/projects/create).
2. Crea un proyecto (p. ej. «ASIR HUB Calendar»).
3. Borra el código de ejemplo y **pega íntegramente** el contenido de [google-apps-script/Code.gs](./google-apps-script/Code.gs). Guarda.
4. En el desplegable de funciones elige **listarCalendarios** y pulsa **Ejecutar**. Autoriza el acceso a tu Google Calendar si se solicita.
5. En el registro de ejecución aparecen los nombres e IDs de los calendarios. Busca exactamente el calendario de Aules (no el calendario personal). **No compartas esos registros ni el ID del calendario por chat**.
6. En **Configuración del proyecto (⚙️) → Propiedades del script**, añade `ASIR_CALENDAR_ID` con ese ID exacto.
7. En el desplegable de funciones elige **crearClave** y pulsa **Ejecutar**. Se genera una clave privada en las propiedades del script.
8. Pulsa **Implementar → Nueva implementación → Aplicación web**. Configura **Ejecutar como: Yo** y **Quién tiene acceso: Cualquier usuario (Anyone)**. Implementa y autoriza los permisos solicitados. El script solo lee el calendario seleccionado y exige clave para responder.
9. Vuelve al editor, selecciona **mostrarEnlacePrivado** y pulsa **Ejecutar**. En su registro aparece una URL que comienza con `https://script.google.com/macros/s/` y contiene `?key=`. **No la publiques ni la envíes a nadie**.

Nota: si el administrador de Google impide desplegar una web para «Cualquier usuario», este método necesita una alternativa. El enlace protegido permite obtener los datos solo con la clave, pero sigue siendo un recurso sensible.

## 3. Configurar GitHub

1. En este repositorio abre [Settings → Secrets and variables → Actions](https://github.com/lianas13/asir-hub/settings/secrets/actions).
2. Pulsa **New repository secret**.
3. Nombre: `GOOGLE_EVENTS_URL`.
4. Valor: la **URL completa** que devolvió `mostrarEnlacePrivado` (incluido `?key=...`).
5. Guarda. **No uses** `AULES_ICS_URL` para este método; el workflow nuevo ya no consulta Aules directamente.
6. En [Settings → Pages](https://github.com/lianas13/asir-hub/settings/pages), selecciona **Source → GitHub Actions**.
7. En [Actions → Publicar ASIR HUB](https://github.com/lianas13/asir-hub/actions/workflows/deploy.yml), ejecuta **Run workflow**.

Cuando el workflow termine en verde, abre **https://lianas13.github.io/asir-hub/**.

## ¿Cómo se actualiza?

- Aules actualiza su calendario de exámenes o entregas.
- **Google Calendar consulta periódicamente Aules**, pero puede tardar horas en refrescar sus suscripciones. No es tiempo real.
- GitHub Actions pide los eventos a Google Apps Script aproximadamente cada 30 minutos, aunque GitHub puede retrasar ejecuciones programadas.
- ASIR HUB publica solo los datos mínimos de fechas y títulos. Si Google o Aules está inaccesible temporalmente, la ejecución falla para no sobrescribir los datos publicados con un calendario vacío.
- Los tipos «Examen», «Entrega» y «Otro» se infieren por palabras del título. Deben comprobarse, porque no todos los eventos se pueden clasificar automáticamente.

## Archivos

- `site/`: web pública HTML, CSS y JavaScript.
- `scripts/sync_calendar.py`: lector privado de Google Apps Script; genera `site/events.json` durante el despliegue.
- `google-apps-script/Code.gs`: código para pegar en un proyecto privado de Apps Script en tu cuenta de Google.
- `.github/workflows/deploy.yml`: sincronización y publicación en GitHub Pages.

El repositorio **no** incluye tokens, contraseñas ni credenciales. La URL con clave se guarda únicamente como secreto de GitHub y en los registros privados de Google Apps Script al mostrarla.
