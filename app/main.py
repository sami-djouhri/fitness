"""Fitness – FastAPI application."""

import os
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes_exercises import router as exercises_router
from app.api.routes_plans import router as plans_router
from app.api.routes_workouts import router as workouts_router
from app.api.routes_progress import router as progress_router
from app.api.routes_body import router as body_router
from app.api.routes_achievements import router as achievements_router
from app.api.routes_admin import router as admin_router
from app.api.routes_anstoss import router as anstoss_router
from app.api.routes_analyse import router as analyse_router
from app.api.routes_profil import router as profil_router
from app.api.routes_jetzt import router as jetzt_router
from app.api.routes_schritte import router as schritte_router
from app.db import SessionLocal
from app.domain import DomainError
import app.tenant  # noqa: F401  (registriert das Multi-Tenant-Scoping fuer Session-Events)

# ---------------------------------------------------------------------------
# In-memory rate limiter: 60 requests per minute per IP
# ---------------------------------------------------------------------------
RATE_LIMIT = 60
RATE_WINDOW = 60  # seconds
_rate_store: dict[str, tuple[int, float]] = {}  # ip -> (count, window_start)
_rate_last_cleanup = time.monotonic()
RATE_CLEANUP_INTERVAL = 300  # 5 minutes


class AutheliaHeaderMiddleware(BaseHTTPMiddleware):
    """Liest Authelia-Header (Remote-User/Remote-Groups) in request.state.
    Soft-Auth: nur Logging-Stempel. Authelia/Edge-Nginx enforced den Zugriff
    am Edge (*.daheim.home). Bei lokalem 127.0.0.1-Direktaufruf sind die
    Header leer.
    """

    async def dispatch(self, request, call_next):
        request.state.user = request.headers.get("remote-user") or ""
        groups_header = request.headers.get("remote-groups") or ""
        request.state.groups = [g.strip() for g in groups_header.split(",") if g.strip()]
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if os.environ.get("FITNESS_RATE_LIMIT_DISABLED") == "1":
            return await call_next(request)

        global _rate_last_cleanup
        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()

        # Periodic cleanup of stale entries
        if now - _rate_last_cleanup > RATE_CLEANUP_INTERVAL:
            stale = [ip for ip, (_, ws) in _rate_store.items() if now - ws > RATE_WINDOW]
            for ip in stale:
                del _rate_store[ip]
            _rate_last_cleanup = now

        count, window_start = _rate_store.get(client_ip, (0, now))
        if now - window_start > RATE_WINDOW:
            # New window
            count, window_start = 1, now
        else:
            count += 1

        _rate_store[client_ip] = (count, window_start)

        if count > RATE_LIMIT:
            return JSONResponse(
                {"error": "Zu viele Anfragen. Bitte warte einen Moment."},
                status_code=429,
            )

        return await call_next(request)


import logging

from app.config import settings
from app.mandant_ableiten import einzigen_mandanten_ableiten

_start_log = logging.getLogger(__name__)

# ★ Einmalige Warnung beim Start, wenn kein Mandant fuer headerlose Aufrufe
# konfiguriert ist. Ohne sie waere der fail-closed-Zustand unsichtbar: interne
# Aufrufer (life-ops, assets-api) bekaemen leere Antworten, und leer sieht aus
# wie "nichts da" statt wie "nicht konfiguriert".
if not settings.DEFAULT_OWNER_SUB:
    _abgeleitet = einzigen_mandanten_ableiten()
    if _abgeleitet:
        settings.DEFAULT_OWNER_SUB = _abgeleitet
        _start_log.warning(
            "DEFAULT_OWNER_SUB war leer und wurde aus den Daten abgeleitet "
            "(genau ein Mandant vorhanden). Dauerhaft eintragen mit "
            "saganta/scripts/owner-kennung-eintragen.sh"
        )
    else:
        _start_log.warning(
            "DEFAULT_OWNER_SUB ist leer und nicht ableitbar. Headerlose interne "
            "Aufrufe sehen keine Daten. Eintragen mit "
            "saganta/scripts/owner-kennung-eintragen.sh"
        )

app = FastAPI(title="Fitness", version="0.1.0")

app.add_middleware(RateLimitMiddleware)
app.add_middleware(AutheliaHeaderMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8094",
        "http://127.0.0.1:8094",
        "http://localhost",
        "https://localhost",
    ],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)

app.include_router(exercises_router)
app.include_router(plans_router)
app.include_router(workouts_router)
app.include_router(progress_router)
app.include_router(body_router)
app.include_router(achievements_router)
app.include_router(admin_router)
app.include_router(anstoss_router)
app.include_router(analyse_router)
app.include_router(profil_router)
app.include_router(schritte_router)
app.include_router(jetzt_router)


@app.get("/health", tags=["health"])
def health():
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        # Die MealPrep-Kopplung ist nachsichtig gebaut: ein Fehlschlag schreibt
        # eine Protokollzeile und gibt False zurueck. Genau so blieb es
        # jahrelang unbemerkt, dass die Adressen ins Leere zeigten. Der
        # Zaehlstand macht den Zustand ablesbar, ohne den Healthcheck rot zu
        # faerben: der Dienst ist auch ohne MealPrep voll benutzbar.
        from app.mqtt import publisher
        from app.services import mealprep_adapter
        return {
            "status": "ok",
            "mealprep": mealprep_adapter.zustand(),
            "benachrichtigung": publisher.zustand(),
        }
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse({"status": "error", "message": str(e)}, status_code=503)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    return JSONResponse(
        status_code=422,
        content={"error": exc.message, "details": exc.details},
    )


def resolve_spa_path(static_root: Path, path: str) -> Path | None:
    """Loest einen SPA-Anfragepfad auf eine auslieferbare Datei auf.

    `path` kommt URL-dekodiert an: aus `/..%2f..%2fdata%2fapp.db` wird hier
    `../../data/app.db`. Ohne Aufloesen + Wurzel-Check liefert der Fallback jede
    fuer den Prozess lesbare Datei aus (SQLite-DB, /etc/passwd, Quellcode).
    Deshalb erst aufloesen (frisst `..` und Symlinks), dann gegen die
    Static-Wurzel pruefen.

    Rueckgabe: die Datei, oder None wenn ausserhalb der Wurzel / nicht vorhanden.
    """
    try:
        candidate = (static_root / path).resolve()
    except OSError:
        return None
    if not candidate.is_relative_to(static_root):
        return None
    return candidate if candidate.is_file() else None


# Serve SPA static files (after all API routers)
_static_dir = Path(__file__).parent / "static"
if _static_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=_static_dir / "assets"), name="assets")

    _static_root = _static_dir.resolve()

    @app.get("/{path:path}", include_in_schema=False)
    async def spa_fallback(path: str):
        file_path = resolve_spa_path(_static_root, path)
        if file_path is not None:
            return FileResponse(file_path)
        return FileResponse(_static_root / "index.html")
