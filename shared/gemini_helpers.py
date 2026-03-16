"""
Helpers compartilhados para integracao com Google Gemini.
"""

import json

import httpx


def safe_json_load(text: str):
    """Parse JSON de resposta do Gemini, removendo markdown fences."""
    if not text or not isinstance(text, str):
        raise ValueError("Resposta vazia ou invalida da IA")

    cleaned = text.strip().replace("```json", "").replace("```", "").strip()

    decoder = json.JSONDecoder()
    for i, ch in enumerate(cleaned):
        if ch in "{[":
            try:
                obj, _ = decoder.raw_decode(cleaned[i:])
                return obj
            except json.JSONDecodeError:
                continue

    raise ValueError(
        "Resposta da IA nao contem JSON valido.\n"
        f"Conteudo recebido:\n{cleaned[:1000]}"
    )


def baixar_arquivo(url: str, timeout: int = 60) -> bytes:
    """Download de arquivo por URL ou leitura de caminho local."""
    if url.startswith("http"):
        return httpx.get(url, timeout=timeout).content
    with open(url, "rb") as f:
        return f.read()
