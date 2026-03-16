"""
Modulo de geracao de PDF a partir de HTML via Playwright (Chromium).

Usado pelo endpoint /gerar-pdf em API.py.
"""

import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

WEBHOOK_SALVAR = "https://n8n.anchieta.br/webhook/salvar-ebook"


def _gerar_pdf_sync(html_content: str) -> bytes:
    """
    Recebe HTML como string e retorna bytes do PDF via Chromium.
    """
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".html", delete=False, mode="w", encoding="utf-8"
        ) as tmp:
            tmp.write(html_content)
            tmp_path = Path(tmp.name)

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(tmp_path.as_uri(), wait_until="networkidle")

            pdf_bytes = page.pdf(
                format="A4",
                print_background=True,
                scale=1.0,
                margin={
                    "top": "0mm",
                    "bottom": "0mm",
                    "left": "0mm",
                    "right": "0mm",
                },
            )
            browser.close()

        return pdf_bytes
    finally:
        if tmp_path:
            tmp_path.unlink(missing_ok=True)
