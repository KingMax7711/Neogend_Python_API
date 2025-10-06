from __future__ import annotations

import json
import logging
from logging.handlers import TimedRotatingFileHandler
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Mapping, Optional
from contextvars import ContextVar
import traceback as _traceback


# Context for request correlation id (used across logs in the same request)
_correlation_id_ctx: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def set_correlation_id(correlation_id: Optional[str]) -> None:
    _correlation_id_ctx.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    return _correlation_id_ctx.get()


class JSONFormatter(logging.Formatter):
    def __init__(self, *, indent: Optional[int] = None) -> None:
        super().__init__()
        self._indent = indent

    def format(self, record: logging.LogRecord) -> str:
        now = datetime.now(timezone.utc).isoformat()
        # Base payload
        payload: Dict[str, Any] = {
            "ts": now,
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", None) or record.getMessage(),
            "message": record.getMessage(),
            "app": {
                "version": os.getenv("APP_VERSION") or None,
                "env": os.getenv("APP_RELEASE_STATUS") or None,
            },
            "corr_id": getattr(record, "correlation_id", None) or get_correlation_id(),
        }

        # user info
        user_id = getattr(record, "user_id", None)
        email = getattr(record, "email", None)
        if user_id is not None or email is not None:
            payload["user"] = {"id": user_id, "email": email}

        # tags
        tags = getattr(record, "tags", None)
        if tags:
            payload["tags"] = tags

        # request info (duck-typed)
        req = getattr(record, "request", None)
        if req is not None:
            try:
                path = getattr(getattr(req, "url", None), "path", None)
                method = getattr(req, "method", None)

                # Try headers first (X-Forwarded-For, X-Real-Ip) — useful behind proxies/load-balancers
                headers = None
                try:
                    headers = req.headers
                except Exception:
                    headers = getattr(req, "headers", None)

                client_ip: Optional[str] = None
                if headers is not None:
                    # starlette Headers is Mapping-like, but be defensive
                    try:
                        xff = headers.get("x-forwarded-for") or headers.get("x-real-ip")
                    except Exception:
                        xff = headers.get("x-forwarded-for") if isinstance(headers, Mapping) else None
                    if xff:
                        # X-Forwarded-For may contain comma-separated list; take first
                        client_ip = xff.split(",")[0].strip()

                # Fallback to request.client (Starlette Address) or scope
                if not client_ip:
                    client = getattr(req, "client", None)
                    if client is not None:
                        # Address may be object with .host or a tuple
                        client_ip = getattr(client, "host", None) if hasattr(client, "host") else (client[0] if isinstance(client, (list, tuple)) and client else None)

                if not client_ip:
                    try:
                        scope = getattr(req, "scope", None)
                        if scope and "client" in scope and scope["client"]:
                            client_ip = scope["client"][0]
                    except Exception:
                        pass

                user_agent = None
                if headers is not None:
                    try:
                        user_agent = headers.get("user-agent")
                    except Exception:
                        user_agent = headers.get("user-agent") if isinstance(headers, Mapping) else None

                payload["request"] = {
                    "method": method,
                    "path": path,
                    "client_ip": client_ip,
                    "user_agent": user_agent,
                }
            except Exception:
                # never break logging on request extraction
                pass

        # attach structured data if provided
        data = getattr(record, "data", None)
        if isinstance(data, dict):
            payload["data"] = data

        # exception info
        err = getattr(record, "error", None)
        if err is not None:
            payload["error"] = {
                "type": type(err).__name__,
                "message": str(err),
                "stack": _traceback.format_exception(type(err), err, err.__traceback__),
            }
        elif record.exc_info:
            etype, evalue, etb = record.exc_info
            payload["error"] = {
                "type": getattr(etype, "__name__", str(etype)),
                "message": str(evalue),
                "stack": _traceback.format_exception(etype, evalue, etb),
            }

        return json.dumps(payload, ensure_ascii=False, indent=self._indent)


def _ensure_logger() -> logging.Logger:
    logger = logging.getLogger("api")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Paths
    base_dir = Path(__file__).resolve().parent
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Console handler (human readable)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(ch)

    # File handler (JSON, daily rotation, keep 14 backups)
    fh = TimedRotatingFileHandler(
        filename=str(logs_dir / "app.log"), when="midnight", interval=1, backupCount=14, encoding="utf-8"
    )
    fh.setLevel(logging.INFO)
    fh.setFormatter(JSONFormatter(indent=None))
    logger.addHandler(fh)

    return logger


_LEVELS_MAP = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}


def _normalize_level(level: int | str) -> int:
    if isinstance(level, int):
        return level
    return _LEVELS_MAP.get(level.upper(), logging.INFO)


_DEFAULT_REDACT_KEYS = {"password", "passwd", "token", "authorization", "secret", "api_key", "x-api-key"}


def _redact(obj: Any, redact_keys: Iterable[str]) -> Any:
    try:
        keys = {k.lower() for k in redact_keys}
        if isinstance(obj, Mapping):
            out: Dict[str, Any] = {}
            for k, v in obj.items():
                if str(k).lower() in keys:
                    out[k] = "***redacted***"
                else:
                    out[k] = _redact(v, keys)
            return out
        if isinstance(obj, list):
            return [_redact(v, keys) for v in obj]
        if isinstance(obj, tuple):
            return tuple(_redact(v, keys) for v in obj)
        return obj
    except Exception:
        return obj


def api_log(
    event: str,
    *,
    level: int | str = "INFO",
    request: Any | None = None,
    user_id: int | None = None,
    email: str | None = None,
    data: Dict[str, Any] | None = None,
    err: BaseException | None = None,
    tags: list[str] | None = None,
    correlation_id: str | None = None,
    redact_keys: Iterable[str] | None = None,
) -> None:
    """Log structurément un évènement API.

    - event: nom/description courte de l'évènement
    - level: niveau ('INFO', 'ERROR', ...) ou int logging
    - request: objet Request (FastAPI) optionnel pour extraire method/path/ip
    - user_id/email: informations utilisateur optionnelles
    - data: dict de données complémentaires (sera redacted sur clés sensibles)
    - err: exception capturée (inclut type/message/stack)
    - tags: liste de tags strings pour filtrage ultérieur
    - correlation_id: ID de corrélation (sinon pris depuis le contexte)
    - redact_keys: clés sensibles à masquer (par défaut: password/token/...)
    """

    logger = _ensure_logger()
    lvl = _normalize_level(level)

    if correlation_id:
        set_correlation_id(correlation_id)

    # sanitize/redact data
    if data is not None:
        data = _redact(data, redact_keys or _DEFAULT_REDACT_KEYS)  # type: ignore[arg-type]

    extra = {
        "event": event,
        "request": request,
        "user_id": user_id,
        "email": email,
        "data": data,
        "tags": tags,
        "correlation_id": correlation_id or get_correlation_id(),
        "error": err,
    }

    # message for console readability
    console_message = event
    if data:
        try:
            console_message += f" | data={json.dumps(data, ensure_ascii=False)}"
        except Exception:
            pass
    if user_id or email:
        console_message += f" | user={email or user_id}"

    logger.log(lvl, console_message, extra=extra, exc_info=err is not None)


__all__ = [
    "api_log",
    "set_correlation_id",
    "get_correlation_id",
]
