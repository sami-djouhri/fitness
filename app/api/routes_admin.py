"""Admin routes: backup export + restore-import."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.services.admin import IMPORT_CONFIRM_TOKEN, AdminService


def require_admin(x_admin_token: str | None = Header(None)) -> None:
    """F1: Admin-Endpunkte (voller DB-Export/-Import) app-seitig gaten.
    Fail-closed: ohne konfiguriertes ADMIN_TOKEN sind die Routen gesperrt."""
    import hmac
    if not settings.ADMIN_TOKEN:
        raise HTTPException(status_code=503, detail="admin endpoints disabled (ADMIN_TOKEN not set)")
    if not x_admin_token or not hmac.compare_digest(x_admin_token, settings.ADMIN_TOKEN):
        raise HTTPException(status_code=401, detail="invalid or missing admin token")


router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/export")
def export_backup(db: Session = Depends(get_db)) -> JSONResponse:
    """Download a full JSON snapshot of every table.

    The result is suitable for archiving (file backup) or future restore via
    POST /api/admin/import. Primary keys are preserved.
    """
    svc = AdminService(db)
    payload = svc.export_all()
    headers = {
        "Content-Disposition": 'attachment; filename="fitness-backup.json"',
    }
    return JSONResponse(content=payload, headers=headers)


@router.post("/import")
def import_backup(
    payload: dict[str, Any] = Body(...),
    confirm: str | None = Query(None, description=f"Must equal '{IMPORT_CONFIRM_TOKEN}' to actually import."),
    dry_run: bool = Query(False, description="If true, only validate + return the manifest, do not mutate."),
    db: Session = Depends(get_db),
):
    """**DESTRUCTIVE**: replace ALL data with the contents of a prior export.

    Safety gates:
    - `dry_run=true` → returns row-count manifest without changes
    - `confirm=I_UNDERSTAND_THIS_REPLACES_ALL_DATA` is required for the mutating path
    - schema_version mismatch returns 400 with the expected version
    - transaction is all-or-nothing: any insert failure rolls back the truncate
    """
    svc = AdminService(db)

    try:
        manifest = svc.validate_import(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not manifest["compatible"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "incompatible_schema_version",
                "schema_version": manifest.get("schema_version"),
                "expected_schema_version": manifest.get("expected_schema_version"),
            },
        )

    if dry_run:
        return {"dry_run": True, **manifest}

    if confirm != IMPORT_CONFIRM_TOKEN:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "missing_or_invalid_confirm_token",
                "hint": f"pass ?confirm={IMPORT_CONFIRM_TOKEN}",
            },
        )

    try:
        result = svc.import_all(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"import failed: {type(e).__name__}: {e}")

    return {"dry_run": False, **result}
