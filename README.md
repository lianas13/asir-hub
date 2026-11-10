# ASIR HUB

Calendario de entregas y exámenes de 2.º ASIR, publicado con GitHub Pages y actualizado desde la exportación ICS de Aules.

## Configuración

1. En Aules, genera una URL de exportación del calendario **solo con eventos de los cursos**. Evita exportar eventos personales. **Nunca la publiques** en el repositorio.
2. Revisa los títulos de los eventos: la web es pública y mostrará sus títulos y fechas. Si el feed contiene datos privados, utiliza otro feed o filtros antes de publicar.
3. En GitHub entra a **Settings → Secrets and variables → Actions → New repository secret**. Nombre: `AULES_ICS_URL`; valor: URL completa de Aules.
4. En **Settings → Pages**, elige **Source: GitHub Actions**.
5. En **Actions → Publicar ASIR HUB → Run workflow**, ejecuta la primera sincronización.
6. Accede a `https://lianas13.github.io/asir-hub/` cuando el despliegue finalice.

La sincronización está programada aproximadamente cada 30 minutos, pero GitHub puede retrasar las ejecuciones. Solo se publican títulos y fechas de eventos; nunca tokens, URLs de Aules, descripciones ni los UID originales.

Opcionalmente, define la variable de Actions `AULES_TITLE_ALLOWLIST` con fragmentos del título de eventos permitidos separados con `||` (por ejemplo: `redes||seguridad||sistemas`). **No es un filtro de privacidad completo**: revisa antes el feed que vas a publicar.

## Arquitectura

- `site/`: HTML/CSS/JavaScript responsive y `events.json` generado al desplegar.
- `scripts/sync_calendar.py`: lee el ICS de forma privada en GitHub Actions y genera un JSON reducido.
- `.github/workflows/deploy.yml`: despliega a GitHub Pages y vuelve a ejecutarse periódicamente.

Los eventos marcados como exámenes/entregas se identifican por palabras en el título. Algunos eventos podrán aparecer como “Otros”. La web no permite crear ni modificar actividades dentro de Aules.

**Importante:** el enlace `AULES_ICS_URL` suele identificar tu sesión/exportación. No se debe compartir ni pegar en chats públicos.
