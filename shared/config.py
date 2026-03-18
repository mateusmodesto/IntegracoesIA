import os
import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env')

# ── Database ─────────────────────────────────────────────────────────────
DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
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
    format='[%(asctime)s] %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Silencia bibliotecas terceiras ruidosas
for _lib in ('werkzeug', 'httpx', 'httpcore', 'urllib3', 'googleapiclient'):
    logging.getLogger(_lib).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
