import os
import logging

from dotenv import load_dotenv

load_dotenv()

# ── Database ─────────────────────────────────────────────────────────────
DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', '192.168.0.9'),
    'port': int(os.getenv('DB_PORT', '1433')),
    'database': os.getenv('DB_NAME', 'dtb_lyceum_prod'),
    'user': os.getenv('DB_USER', 'lyceum'),
    'password': os.getenv('DB_PASSWORD', 'lyceum'),
}

# ── Gemini API ───────────────────────────────────────────────────────────
GEMINI_API_KEY_PRIMARY = os.getenv('GEMINI_API_KEY_PRIMARY', '')
GEMINI_API_KEY_PROUNI = os.getenv('GEMINI_API_KEY_PROUNI', '')

# ── AWS ──────────────────────────────────────────────────────────────────
AWS_API_KEY = os.getenv('AWS_API_KEY', '')

# ── Flask ────────────────────────────────────────────────────────────────
FLASK_PORT = int(os.getenv('FLASK_PORT', '5010'))

# ── Logging ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
