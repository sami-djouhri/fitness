from fastapi import Request
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.backend_auth import sub_from_bearer
from app.config import settings
from app.tenant_auth import loese_owner_sub

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=False,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db(request: Request) -> Session:  # type: ignore[misc]
    # Tenant an die Session binden. Drei Pfade (wie lager):
    #  1. Nativer Client: `Authorization: Bearer <HS256-JWT>` (aud=fitness-api) →
    #     fail-closed verifiziert (jeder Fehler = 401, KEIN Default-Fallback).
    #  2. Web via app-proxy: `X-Saganta-Sub`-Header (better-auth-sub), seit
    #     2026-09-05 mit HMAC-Signatur pruefbar (app/tenant_auth.py, FCS-01).
    #  3. Interne/headerlose Aufrufe → DEFAULT_OWNER_SUB (bisheriges Verhalten).
    # Scoping via app/tenant.py aus session.info.
    authorization = request.headers.get("authorization", "")
    if authorization.startswith("Bearer "):
        owner_sub = sub_from_bearer(authorization)
    else:
        owner_sub = loese_owner_sub(request)

    db = SessionLocal()
    db.info["owner_sub"] = owner_sub
    try:
        yield db  # type: ignore[misc]
    finally:
        db.close()
