"""
Serviço de monitoramento em background.

Responsabilidades:
  - Heartbeat a cada HEARTBEAT_INTERVAL segundos (status do container)
  - Snapshot de métricas do sistema a cada METRICS_INTERVAL segundos
  - Snapshot de métricas da API a cada STATS_INTERVAL segundos

Estrutura no Firestore:
  monitoring/
    {app_name}/
      heartbeat           ← documento único, sobrescrito
      system_metrics/     ← subcoleção, um doc por coleta
      api_stats           ← documento único, sobrescrito
      api_events/         ← subcoleção, um doc por requisição (via app_monitor)
"""

import os
import time
import logging
import threading
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ── Intervalos configuráveis via .env ─────────────────────────────────────
HEARTBEAT_INTERVAL = int(os.getenv("MONITORING_HEARTBEAT_INTERVAL", "30"))   # segundos
METRICS_INTERVAL   = int(os.getenv("MONITORING_METRICS_INTERVAL",   "60"))   # segundos
STATS_INTERVAL     = int(os.getenv("MONITORING_STATS_INTERVAL",     "120"))  # segundos


def _app_name() -> str:
    return os.getenv("MONITORING_APP_NAME", "flask_api")


# ── Rotinas de envio ──────────────────────────────────────────────────────

def _push_heartbeat():
    """Atualiza o documento de heartbeat — confirma que o container está vivo."""
    try:
        from monitoring.firebase_client import set_document
        from monitoring.system_monitor import _container_id, _uptime_seconds, _format_uptime

        uptime = _uptime_seconds()
        set_document(
            collection=f"monitoring/{_app_name()}",
            doc_id="heartbeat",
            data={
                "status": "running",
                "container_id": _container_id(),
                "uptime_seconds": uptime,
                "uptime_formatted": _format_uptime(uptime),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        logger.debug("[monitoring] heartbeat enviado")
    except Exception as exc:
        logger.warning(f"[monitoring] heartbeat falhou: {exc}")


def _push_system_metrics():
    """Coleta e persiste métricas do sistema como novo documento na subcoleção."""
    try:
        from monitoring.firebase_client import save_document
        from monitoring.system_monitor import collect_metrics

        metrics = collect_metrics()
        save_document(f"monitoring/{_app_name()}/system_metrics", metrics)
        logger.debug(
            f"[monitoring] system_metrics salvo — "
            f"cpu={metrics['cpu']['percent']}% "
            f"mem={metrics['memory']['percent']}% "
            f"disco={metrics['disk']['percent']}%"
        )
    except Exception as exc:
        logger.warning(f"[monitoring] system_metrics falhou: {exc}")


def _push_api_stats():
    """Persiste snapshot dos contadores de API como documento único (sobrescrito)."""
    try:
        from monitoring.firebase_client import set_document
        from monitoring.app_monitor import get_api_stats

        stats = get_api_stats()
        set_document(
            collection=f"monitoring/{_app_name()}",
            doc_id="api_stats",
            data=stats,
        )
        logger.debug(
            f"[monitoring] api_stats salvo — "
            f"total={stats['total_requests']} erros={stats['total_errors']}"
        )
    except Exception as exc:
        logger.warning(f"[monitoring] api_stats falhou: {exc}")


# ── Loop principal ────────────────────────────────────────────────────────

def _run():
    """
    Loop de monitoramento que roda em background.
    Usa contadores independentes para cada tipo de coleta.
    """
    logger.info(
        f"[monitoring] serviço iniciado — "
        f"heartbeat={HEARTBEAT_INTERVAL}s "
        f"metrics={METRICS_INTERVAL}s "
        f"stats={STATS_INTERVAL}s"
    )

    last_heartbeat = 0.0
    last_metrics   = 0.0
    last_stats     = 0.0

    while True:
        now = time.monotonic()

        if now - last_heartbeat >= HEARTBEAT_INTERVAL:
            _push_heartbeat()
            last_heartbeat = now

        if now - last_metrics >= METRICS_INTERVAL:
            _push_system_metrics()
            last_metrics = now

        if now - last_stats >= STATS_INTERVAL:
            _push_api_stats()
            last_stats = now

        time.sleep(5)  # granularidade do loop


# ── Inicialização ─────────────────────────────────────────────────────────

def start():
    """
    Inicia o serviço de monitoramento em uma thread daemon.

    Se FIREBASE_CREDENTIALS_PATH não estiver configurado, registra um aviso
    e não inicia (a aplicação continua funcionando normalmente).
    """
    creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "")
    if not creds_path:
        logger.warning(
            "[monitoring] FIREBASE_CREDENTIALS_PATH não configurado — "
            "monitoramento desativado. Defina a variável no .env para ativar."
        )
        return

    thread = threading.Thread(target=_run, daemon=True, name="MonitoringService")
    thread.start()
    logger.info(f"[monitoring] thread iniciada (app={_app_name()})")
