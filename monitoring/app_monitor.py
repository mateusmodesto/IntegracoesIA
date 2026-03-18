"""
Middleware Flask para monitoramento de requisições.

Registra: método, endpoint, status code, duração e erros.
Os dados são acumulados em memória e salvos no Firebase periodicamente
pelo MonitoringService, além de um registro individual por requisição.
"""

import time
import threading
import logging
from datetime import datetime, timezone
from collections import defaultdict

logger = logging.getLogger(__name__)

# ── Estado em memória (thread-safe via Lock) ──────────────────────────────

_lock = threading.Lock()

_stats = {
    "total_requests": 0,
    "total_errors": 0,       # status >= 400
    "total_5xx": 0,          # status >= 500
    "endpoints": defaultdict(lambda: {
        "count": 0,
        "errors": 0,
        "total_ms": 0.0,
    }),
}

# Atributo usado para medir duração via before/after_request
_REQUEST_START_ATTR = "_monitoring_start"


# ── Hooks Flask ───────────────────────────────────────────────────────────

def before_request_hook():
    """Registra o timestamp de início da requisição no contexto Flask."""
    import flask
    setattr(flask.g, _REQUEST_START_ATTR, time.perf_counter())


def after_request_hook(response, *, save_to_firebase: bool = True):
    """
    Captura métricas após cada requisição e:
    1. Atualiza contadores em memória.
    2. Persiste o evento individualmente no Firebase (assíncrono).
    """
    import flask

    try:
        start = getattr(flask.g, _REQUEST_START_ATTR, None)
        duration_ms = round((time.perf_counter() - start) * 1000, 1) if start else -1

        method = flask.request.method
        endpoint = flask.request.path
        status = response.status_code
        is_error = status >= 400

        # Atualiza contadores em memória
        with _lock:
            _stats["total_requests"] += 1
            if is_error:
                _stats["total_errors"] += 1
            if status >= 500:
                _stats["total_5xx"] += 1

            ep = _stats["endpoints"][endpoint]
            ep["count"] += 1
            if is_error:
                ep["errors"] += 1
            if duration_ms > 0:
                ep["total_ms"] += duration_ms

        # Persiste evento individual no Firebase em background
        if save_to_firebase:
            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "method": method,
                "endpoint": endpoint,
                "status_code": status,
                "duration_ms": duration_ms,
                "is_error": is_error,
            }
            threading.Thread(
                target=_persist_event,
                args=(event,),
                daemon=True,
            ).start()

    except Exception as exc:
        logger.debug(f"[monitoring] after_request_hook error: {exc}")

    return response


def _persist_event(event: dict):
    """Salva um evento de requisição no Firebase (executado em thread separada)."""
    try:
        from monitoring.firebase_client import save_document
        app_name = _get_app_name()
        save_document(f"monitoring/{app_name}/api_events", event)
    except Exception as exc:
        logger.debug(f"[monitoring] falha ao salvar evento no Firebase: {exc}")


# ── Leitura de métricas acumuladas ────────────────────────────────────────

def get_api_stats() -> dict:
    """Retorna snapshot dos contadores em memória."""
    with _lock:
        endpoints_summary = {}
        for path, ep in _stats["endpoints"].items():
            avg_ms = round(ep["total_ms"] / ep["count"], 1) if ep["count"] > 0 else 0
            endpoints_summary[path] = {
                "count": ep["count"],
                "errors": ep["errors"],
                "avg_ms": avg_ms,
            }

        return {
            "total_requests": _stats["total_requests"],
            "total_errors": _stats["total_errors"],
            "total_5xx": _stats["total_5xx"],
            "endpoints": endpoints_summary,
            "snapshot_at": datetime.now(timezone.utc).isoformat(),
        }


def _get_app_name() -> str:
    """Nome da aplicação para usar como chave no Firebase."""
    import os
    return os.getenv("MONITORING_APP_NAME", "flask_api")
