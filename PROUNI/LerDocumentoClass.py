"""
Integracao com Google Gemini para validacao e extracao de documentos PROUNI.

Fluxo:
    1. analisar_documento() recebe URL + tipo esperado
    2. Etapa 1 (flash-lite): valida se o documento bate com o tipo informado
    3. Etapa 2 (flash): extrai dados estruturados (so se validacao passou)
"""

import os
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional

import requests
from google import genai
from google.genai import types

from shared.config import GEMINI_API_KEY_PROUNI
from shared.gemini_helpers import safe_json_load, baixar_arquivo

# ── Modelos Gemini ────────────────────────────────────────────────────────
MODELO_VALIDACAO = "gemini-2.5-flash-lite"
MODELO_EXTRACAO = "gemini-2.5-flash"

# ── Extensoes suportadas ──────────────────────────────────────────────────
MIME_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "tiff": "image/tiff",
    "pdf": "application/pdf",
}

# ── Prompt base de validacao ──────────────────────────────────────────────
PROMPT_VALIDACAO = """
Voce e um extrator de dados de documentos brasileiros a partir de PDFs e imagens (scans de documentos fisicos).

Sua tarefa e:
1. Ler o arquivo (PDF ou imagem) recebido.
2. Identificar qual e o tipo de documento.
3. Comparar para ver se realmente bate com o tipo de documento informado no campo "tipo_documento".
4. Retornar o JSON com as informacoes extraidas.

FORMATO GERAL DO JSON:
{
    "document_informado": "<tipo_documento_informado>",
    "document_type": "<tipo_do_documento>",
    "is_valid": true | false,
    "observations": "comentarios curtos ou vazio se nada a observar"
}

Se nao for possivel identificar o documento:
{
    "document_type": "desconhecido",
    "document_informado": "<tipo_documento_informado>",
    "is_valid": false,
    "observations": "nao foi possivel identificar o documento"
}

Retorne APENAS o JSON, sem texto extra.
"""

# ── Regras de validacao por tipo de documento ─────────────────────────────
REGRAS_VALIDACAO: Dict[str, str] = {
    "CPF": """
        REGRAS DE VALIDACAO:
        1. Se o documento informado for CPF e o documento identificado for RG OU CNH, entao is_valid = true.
    """,
    "RG": """
        REGRAS DE VALIDACAO:
        1. Se o documento informado for RG e o documento identificado for CNH, entao is_valid = true.
    """,
    "HISTORICO_ESCOLAR": """
        REGRAS DE VALIDACAO:
        1. Se o documento informado for Historico Escolar do Ensino Medio ou Certificado de Conclusao
           de Ensino Medio ou Declaracao de Conclusao ou algo que defina que terminou o ensino medio,
           mas caso o documento identificado for de algum outro tipo de documento escolar, entao is_valid = false.
           Deve aceitar apenas do ensino medio.
    """,
    "Declaracao de auxilio financeiro": """
        REGRAS DE VALIDACAO:
        1. Considere valido (is_valid=true) qualquer documento que traga evidencia explicita de
           recebimento de auxilio/beneficio/renda externa (ex.: Bolsa Familia/Auxilio Brasil,
           INSS/aposentadoria/pensao/BPC, seguro-desemprego, pensao alimenticia ou credito
           bancario identificado como beneficio). Se nao houver essa evidencia, is_valid=false.
    """,
    "CTPS - Qualificacao Civil": "",
    "CTPS - Pagina Em Branco": """
        REGRAS DE VALIDACAO:
        1. O documento so devera ser considerado valido se for uma pagina de contrato de trabalho
           em branco da CTPS.
    """,
    "CTPS - Ultimo Contrato": """
        REGRAS DE VALIDACAO:
        1. O documento so devera ser considerado valido se for uma pagina de contrato de trabalho da CTPS.
    """,
    "declaracao de renda": """
        REGRAS DE VALIDACAO:
        1. Considere valido (is_valid=true) qualquer documento que mostre de forma explicita uma
           renda/entrada de dinheiro (holerite, extrato bancario com creditos, declaracao de
           rendimentos, comprovante de aposentadoria/pensao/beneficio, recibo de pagamento ou
           contrato que informe valor de remuneracao). Se nao houver evidencia, is_valid=false.
    """,
    "pro-labore": """
        REGRAS DE VALIDACAO:
        1. Considere valido (is_valid=true) qualquer documento que indique explicitamente pagamento
           de pro-labore ao titular (demonstrativo/recibo, holerite com "pro-labore", extrato com
           credito identificado como pro-labore ou declaracao contabil da empresa informando o valor).
           Se nao houver mencao explicita a pro-labore, is_valid=false.
    """,
    "Comprovante de Residencia / Dec. que mora sozinho": """
        REGRAS DE VALIDACAO:
        1. Considere valido (is_valid=true) qualquer documento que comprove endereco residencial
           do titular ou uma declaracao explicita de que a pessoa mora sozinha.
        2. Exemplos aceitos: contas de consumo, fatura de cartao, correspondencia oficial,
           contrato de aluguel, boleto/documento bancario com endereco.
        3. Tambem aceita declaracao assinada informando residencia ou que mora sozinho.
        4. Se nao contiver endereco identificavel nem declaracao explicita, is_valid=false.
    """,
}

# ── Prompt de extracao de holerite ────────────────────────────────────────
PROMPT_EXTRACAO_HOLERITE = """
Voce e um extrator de dados de holerites brasileiros a partir de PDFs e imagens.

Extraia as seguintes informacoes:
- Salario
- Adicionais
- Salario Bruto
- Salario Liquido
- Descontos

Retorne um JSON neste formato:
{
    "salario": "valor ou null",
    "adicionais": {"tipo_do_adicional": "valor"},
    "salario_bruto": "valor ou null",
    "salario_liquido": "valor ou null",
    "descontos": {"tipo_do_desconto": "valor"},
    "observations": "comentarios curtos ou vazio"
}
"""


class GeminiProuni:
    """Cliente Gemini especializado em documentos PROUNI."""

    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY_PROUNI)

    # ── Metodo principal ──────────────────────────────────────────────────

    def analisarDocumento(self, url: str, tipo_doc: str) -> Dict[str, Any]:
        """Alias para retrocompatibilidade."""
        return self.analisar_documento(url, tipo_doc)

    def analisar_documento(self, url: str, tipo_doc: str) -> Dict[str, Any]:
        """
        Analisa um documento: valida o tipo e, se valido, extrai dados.

        Args:
            url: URL ou caminho local do arquivo.
            tipo_doc: Tipo de documento esperado (ex: 'CPF', 'RG').

        Returns:
            Dict com chaves 'validacao' e opcionalmente 'extracao'.
        """
        ext = url.rsplit(".", 1)[-1].lower()

        if ext == "docx":
            return self._processar_docx(url, tipo_doc)

        mime_type = MIME_TYPES.get(ext)
        if not mime_type:
            return {"Erro": True, "Motivo": f"Extensao '{ext}' nao suportada"}

        return self._processar_documento(url, tipo_doc, mime_type)

    # ── Pipeline padrao (imagem / pdf) ────────────────────────────────────

    def _processar_documento(self, url: str, tipo_doc: str, mime_type: str) -> Dict[str, Any]:
        """Executa validacao e extracao em duas etapas."""
        retorno: Dict[str, Any] = {}

        try:
            doc_bytes = baixar_arquivo(url)
        except Exception as e:
            return {"Erro": True, "Motivo": f"Falha ao baixar arquivo: {e}"}

        # Etapa 1: Validacao
        retorno["validacao"] = self._validar(doc_bytes, mime_type, tipo_doc)

        # Etapa 2: Extracao (so se validou)
        if retorno["validacao"].get("is_valid"):
            retorno["extracao"] = self._extrair(doc_bytes, mime_type, tipo_doc)

        return retorno

    # ── Pipeline DOCX (converte para PDF primeiro) ────────────────────────

    def _processar_docx(self, url: str, tipo_doc: str) -> Dict[str, Any]:
        """Converte DOCX para PDF via LibreOffice e processa."""
        retorno: Dict[str, Any] = {}
        project_dir = os.getcwd()
        safe_tipo = str(tipo_doc).replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_id = f"{safe_tipo}_{timestamp}"

        docx_path = os.path.join(project_dir, f"{file_id}.docx")
        pdf_path = os.path.join(project_dir, f"{file_id}.pdf")

        try:
            # Baixar DOCX
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            with open(docx_path, "wb") as f:
                f.write(resp.content)

            # Converter via LibreOffice headless
            libreoffice = os.getenv("LIBREOFFICE_PATH", r"C:\Program Files\LibreOffice\program\soffice.exe")
            subprocess.run(
                [libreoffice, "--headless", "--convert-to", "pdf", "--outdir", project_dir, docx_path],
                check=True,
            )

            generated_pdf = docx_path.replace(".docx", ".pdf")
            os.rename(generated_pdf, pdf_path)

            retorno = self._processar_documento(pdf_path, tipo_doc, "application/pdf")

        except Exception as e:
            retorno = {"Erro": True, "Motivo": str(e)}

        finally:
            for path in (docx_path, pdf_path):
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass

        return retorno

    # ── Etapa 1: Validacao ────────────────────────────────────────────────

    def _validar(self, doc_bytes: bytes, mime_type: str, tipo_doc: str) -> Dict[str, Any]:
        """Chama Gemini flash-lite para validar tipo do documento."""
        regra = REGRAS_VALIDACAO.get(tipo_doc, "")
        prompt = PROMPT_VALIDACAO + regra + f"\nO tipo de documento informado e: {tipo_doc}"

        try:
            response = self.client.models.generate_content(
                model=MODELO_VALIDACAO,
                contents=[
                    types.Part.from_bytes(data=doc_bytes, mime_type=mime_type),
                    prompt,
                ],
            )
            return safe_json_load(response.text)
        except Exception as e:
            return {"Erro": True, "Motivo": str(e)}

    # ── Etapa 2: Extracao ─────────────────────────────────────────────────

    def _extrair(self, doc_bytes: bytes, mime_type: str, tipo_doc: str) -> Optional[Dict[str, Any]]:
        """Chama Gemini flash para extrair dados do documento."""
        if "holerite" not in tipo_doc.lower():
            return None

        try:
            response = self.client.models.generate_content(
                model=MODELO_EXTRACAO,
                contents=[
                    types.Part.from_bytes(data=doc_bytes, mime_type=mime_type),
                    PROMPT_EXTRACAO_HOLERITE,
                ],
            )
            return safe_json_load(response.text)
        except Exception as e:
            return {"Erro": True, "Motivo": str(e)}


# ── Retrocompatibilidade ──────────────────────────────────────────────────
# API.py e simple_main_flask.py importam "from .LerDocumentoClass import Gemini"
Gemini = GeminiProuni
