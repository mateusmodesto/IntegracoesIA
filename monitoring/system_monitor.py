"""
Coleta métricas do sistema (CPU, RAM, disco, uptime).

Compatível com execução dentro de container Docker — usa /proc quando disponível,
com fallback via psutil para Windows/Mac (ambiente de desenvolvimento).
"""

import os
import time
import logging
import platform
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_start_time = time.time()  # momento em que o processo foi iniciado


def _uptime_seconds() -> float:
    """Segundos desde o início do processo Flask."""
    return round(time.time() - _start_time, 1)


def _format_uptime(seconds: float) -> str:
    """Formata segundos em string legível (ex: '2d 3h 45m 10s')."""
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def _cpu_percent() -> float:
    """Percentual de uso de CPU (1 segundo de amostragem)."""
    try:
        import psutil
        return round(psutil.cpu_percent(interval=1), 1)
    except ImportError:
        return -1.0


def _memory_info() -> dict:
    """Informações de memória RAM em MB e percentual."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        return {
            "total_mb": round(mem.total / 1024 / 1024, 1),
            "used_mb": round(mem.used / 1024 / 1024, 1),
            "available_mb": round(mem.available / 1024 / 1024, 1),
            "percent": round(mem.percent, 1),
        }
    except ImportError:
        return {"total_mb": -1, "used_mb": -1, "available_mb": -1, "percent": -1}


def _disk_info(path: str = "/") -> dict:
    """Informações de disco em GB e percentual."""
    try:
        import psutil
        disk = psutil.disk_usage(path)
        return {
            "total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
            "used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
            "free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
            "percent": round(disk.percent, 1),
        }
    except Exception:
        return {"total_gb": -1, "used_gb": -1, "free_gb": -1, "percent": -1}


def _network_info() -> dict:
    """Bytes enviados/recebidos desde o início do processo."""
    try:
        import psutil
        net = psutil.net_io_counters()
        return {
            "bytes_sent_mb": round(net.bytes_sent / 1024 / 1024, 2),
            "bytes_recv_mb": round(net.bytes_recv / 1024 / 1024, 2),
        }
    except Exception:
        return {"bytes_sent_mb": -1, "bytes_recv_mb": -1}


def _container_id() -> str:
    """
    Tenta detectar o ID do container Docker lendo /proc/self/cgroup.
    Retorna 'local' fora de containers.
    """
    try:
        with open("/proc/self/cgroup", "r") as f:
            for line in f:
                if "docker" in line or "containerd" in line:
                    parts = line.strip().split("/")
                    if parts:
                        cid = parts[-1]
                        if len(cid) >= 12:
                            return cid[:12]
    except Exception:
        pass
    return "local"


def collect_metrics() -> dict:
    """
    Coleta todas as métricas do sistema e retorna um dicionário
    pronto para ser salvo no Firebase.
    """
    uptime = _uptime_seconds()
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "container_id": _container_id(),
        "platform": platform.system(),
        "python_version": platform.python_version(),
        "uptime_seconds": uptime,
        "uptime_formatted": _format_uptime(uptime),
        "cpu": {
            "percent": _cpu_percent(),
            "count": os.cpu_count() or -1,
        },
        "memory": _memory_info(),
        "disk": _disk_info("/"),
        "network": _network_info(),
    }
