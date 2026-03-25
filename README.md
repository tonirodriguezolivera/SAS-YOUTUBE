# YouTube Automator (SaaS base en Flask)

Plataforma multiusuario para conectar canales de YouTube, guardar claves de IA cifradas, definir perfiles de automatización y ejecutar un **pipeline editorial por fases** (idea → títulos → guion → plan → assets → render → QA → publicación → analítica), con jobs invocables por cron.

## Requisitos

- Python **3.11+** (recomendado; en 3.10 también funciona)
- Cuenta Google Cloud con OAuth y APIs de YouTube habilitadas (para conectar canales)

## Instalación rápida

```powershell
cd "ruta\al\proyecto"
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
```

**Importante:** guarda `.env` en **UTF-8** (sin BOM UTF-16). Si ves errores al ejecutar `flask` por codificación, usa temporalmente:

```powershell
$env:FLASK_SKIP_DOTENV="1"
```

y define variables en el sistema o en un `.env` UTF-8.

## Variables de entorno

Ver `.env.example`. Las más críticas:

| Variable | Descripción |
|----------|-------------|
| `SECRET_KEY` | Clave de sesión y CSRF |
| `FERNET_KEY` | Cifrado de tokens y API keys (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`) |
| `DATABASE_URL` | Opcional; por defecto SQLite en `instance/app.db` |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | OAuth YouTube |
| `GOOGLE_OAUTH_REDIRECT_URI` | Debe coincidir con la consola Google (p. ej. `http://127.0.0.1:5000/youtube/oauth/callback`) |

## Estructura

- **`app.py`** (raíz): expone `app` para `flask run` y la CLI de Flask.
- **`application.py`**: factoría `create_app()` (no se llama `app.py` el módulo de la factoría para evitar choque de nombres con el fichero `app.py`).
- **Carpetas en la raíz** (`auth/`, `core/`, `youtube/`, `templates/`, `static/`, …): código y plantillas del producto.

## Base de datos (Alembic / Flask-Migrate)

```powershell
$env:FLASK_APP="app.py"
.\.venv\Scripts\python -m flask db upgrade
```

Tras cambiar modelos:

```powershell
.\.venv\Scripts\python -m flask db migrate -m "descripcion"
.\.venv\Scripts\python -m flask db upgrade
```

## Arrancar la aplicación

Desde la **raíz del repositorio** (donde está `app.py`):

```powershell
.\.venv\Scripts\python -m flask run
```

Con `.flaskenv` ya viene `FLASK_APP=app.py`. Si no usas dotenv:

```powershell
$env:FLASK_APP="app.py"
.\.venv\Scripts\python -m flask run
```

También puedes:

```powershell
.\.venv\Scripts\python app.py
```

Registro, login, dashboard, proveedores, automatizaciones y OAuth YouTube están en rutas bajo `/`, `/auth`, `/youtube`, etc.

### Si aparece `ModuleNotFoundError` (p. ej. `structlog`)

Estás usando el `flask` del **Python global** (suele estar en `AppData\Roaming\Python\...`), no el del **venv** del proyecto. Las dependencias están solo en `.venv`.

**Usa siempre el intérprete del venv:**

```powershell
.\.venv\Scripts\Activate.ps1
flask run
```

o sin activar:

```powershell
.\.venv\Scripts\python -m flask run
```

### Solo Python global (sin venv)

Puedes instalar todo en el mismo intérprete que usa `flask` en la terminal:

```powershell
cd "ruta\al\proyecto"
python -m pip install -r requirements.txt
python -m pip install --upgrade pyopenssl cryptography
flask run
```

Si antes fallaba YouTube con `OpenSSL` / `X509_V_FLAG_NOTIFY_POLICY`, la **actualización de PyOpenSSL** suele arreglarlo. Ojo: en un Python global sueles tener **más proyectos**; pip puede avisar de conflictos con otros paquetes (`googletrans` y versiones fijas de `httpx`, etc.). Para aislar dependencias, el venv sigue siendo lo más limpio.

## Comandos cron (`flask jobs`)

Pensados para ser llamados por el programador de tareas o cron **sin workers obligatorios**:

```text
flask jobs seed-content          # Fase A: nuevas ContentIdea por perfil activo
flask jobs process-pipeline      # Fase B (placeholder): títulos + PipelineRun
flask jobs publish-due           # Publicación pendiente (esqueleto)
flask jobs refresh-youtube-tokens
flask jobs sync-analytics        # Esqueleto Analytics API
```

Ejemplo (Linux cron):

```cron
*/15 * * * * cd /opt/app && .venv/bin/flask jobs process-pipeline >> /var/log/yt-auto.log 2>&1
0 * * * * cd /opt/app && .venv/bin/flask jobs refresh-youtube-tokens >> /var/log/yt-yt.log 2>&1
```

## Conectar YouTube

1. En Google Cloud Console, crea credenciales OAuth 2.0 (aplicación web).
2. Añade la URI de redirección igual a `GOOGLE_OAUTH_REDIRECT_URI`.
3. Habilita **YouTube Data API v3** y **YouTube Analytics API**.
4. En la app: **YouTube → Conectar con Google** (scopes: upload, readonly, analytics).

Los tokens se guardan **cifrados** en `youtube_channels`.

## Registrar API keys de IA

**Proveedores → Añadir**: OpenAI, Gemini (LLM), Veo (vídeo, esqueleto), Runway, ElevenLabs. Las claves se validan con una llamada ligera cuando el proveedor lo permite; se almacenan cifradas y **no se vuelven a mostrar**.

## Arquitectura (módulos)

| Carpeta | Rol |
|---------|-----|
| `auth/`, `users/` | Autenticación, perfil |
| `youtube/` | OAuth, canales, refresh de tokens |
| `providers/` | CRUD + abstracciones `BaseLLMProvider`, `BaseVideoProvider`, `BaseVoiceProvider` |
| `automations/` | Perfiles de automatización (frecuencia, prompt maestro, proveedores, canal) |
| `pipeline/` | Orquestación por fases, penalización por repetición (`repetition.py`) |
| `publishing/`, `analytics/` | Publicación y métricas (extensiones fase 3–4) |
| `dashboard/` | KPIs, auditoría, vista de pipeline |
| `core/` | Modelos, cifrado, auditoría, excepciones |
| `cli/` | Grupo Click `flask jobs` |

Las rutas son finas; la lógica vive en **servicios** y **repositorios** donde aplica.

## Flujo del sistema (visión)

1. El usuario configura **canales** y **proveedores**.
2. Crea **automatizaciones** con prompt maestro y frecuencia.
3. **Cron** ejecuta `seed-content` y `process-pipeline` (en producción, fase 2+ con LLM real generará lotes de títulos con scores, hooks y `reasoning_summary`).
4. Cadena: títulos persistidos → guiones → planes → assets → render → QA scores → `PublicationJob` → `PublishedVideo` → `AnalyticsSnapshot`.
5. El **dashboard** muestra KPIs, auditoría y el **PipelineRun** (Idea → … → Publicado).

## Tests

```powershell
.\.venv\Scripts\python -m pytest
```

## Próximos pasos sugeridos

- **Fase 2:** generación masiva de títulos y guiones con el LLM elegido; deduplicación semántica; registro en `ContentUsageRecord`.
- **Fase 3:** TTS real, vídeo IA, ensamblaje ffmpeg, subida YouTube con `video.insert`.
- **Fase 4:** Analytics + ajuste de parámetros (duración, hooks, CTAs) según métricas.

## Licencia

Uso interno / elige licencia según tu producto.
