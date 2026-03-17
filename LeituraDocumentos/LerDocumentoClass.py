import os
import subprocess
from datetime import datetime
from typing import Any, Dict, Optional

from google import genai
from google.genai import types

from shared.config import GEMINI_API_KEY_PRIMARY
from shared.gemini_helpers import safe_json_load, baixar_arquivo

# ---------------------------------------------------------------------------
# Constantes de modelo
# ---------------------------------------------------------------------------
MODELO_VALIDACAO: str = "gemini-2.5-flash-lite"
MODELO_EXTRACAO: str = "gemini-2.5-flash"

# ---------------------------------------------------------------------------
# Mapeamento extensao -> MIME type
# ---------------------------------------------------------------------------
MIME_TYPES: Dict[str, str] = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "tiff": "image/tiff",
    "pdf": "application/pdf",
}

# ---------------------------------------------------------------------------
# ETAPA 1: Prompt de identifica\u00e7\u00e3o e valida\u00e7\u00e3o
# ---------------------------------------------------------------------------
PROMPT_VALIDACAO: str = """

            Voc\u00ea \u00e9 um identificador de documentos brasileiros a partir de PDFs e imagens.

            Sua tarefa \u00e9:
            1. Ler o arquivo (PDF ou imagem) recebido.
            2. Identificar qual \u00e9 o tipo de documento.
            3. Comparar o documento identificado com o tipo de documento esperado (informado externamente).
            4. Aplicar as regras de substitui\u00e7\u00e3o para verificar se o documento \u00e9 aceito.
            5. Verificar se o tipo de documento \u00e9 aceito para a origem da entrega informada.
            6. Responder SEMPRE com um \u00fanico objeto JSON, sem qualquer texto extra.

            --------------------------------
            VALIDA\u00c7\u00c3O POR ORIGEM
            --------------------------------

            origem_entrega = "pos_graduacao":
            Aceitar:
            - rg, cpf, cnh, certidao_nascimento, certidao_casamento, comprovante_residencia
            - conclusao_historico (gradua\u00e7\u00e3o ou superior)

            origem_entrega = "graduacao":
            Aceitar:
            - rg, cpf, cnh, certidao_nascimento, certidao_casamento, comprovante_residencia
            - certificado_reservista, titulo_eleitor
            - conclusao_historico (**EXCLUSIVAMENTE** Ensino Médio - REJEITAR Ensino Fundamental e Ensino Superior)

            origem_entrega = "escola":
            Aceitar:
            - rg, cpf, cnh, certidao_nascimento, certidao_casamento, comprovante_residencia
            - carteira_vacinacao, declaracao_transferencia
            - conclusao_historico (**Apenas** Ensino Fundamental)

            --------------------------------
            REGRAS DE SUBSTITUI\u00c7\u00c3O
            --------------------------------

            - CNH pode ser entregue no lugar do RG ou do CPF (is_valid = true).
            - RG pode ser entregue no lugar do CPF (is_valid = true).
            - CPF N\u00c3O pode ser entregue no lugar do RG (is_valid = false).
            - comprovante_residencia pode ser qualquer documento que contenha nome, endere\u00e7o e CEP (contas banc\u00e1rias, contas de consumo, contratos, comunicados oficiais, etc). Por\u00e9m, para este caso, **sempre ser\u00e1 marcado como "comprovante_residencia"**, independente do tipo de documento enviado. (document_type = "comprovante_residencia").

            --------------------------------
            REGRAS
            --------------------------------

            - N\u00c3O tente inferir a origem a partir do conte\u00fado do documento.
            - Apenas utilize a origem informada para validar se o documento \u00e9 aceito ou n\u00e3o.
            - Para `conclusao_historico`, identifique o n\u00edvel de ensino (fundamental/medio/superior) e valide conforme a origem.
            - Se n\u00e3o for poss\u00edvel identificar o documento, use "desconhecido".
            - Se o documento informado for "comprovante_residencia" (document_type = "comprovante_residencia"), marque sempre o `document_type` como "comprovante_residencia", **independente do conte\u00fado do documento**.

            --------------------------------
            FORMATO DO JSON
            --------------------------------

            Caso o documento seja identificado corretamente:

            {
            "document_expected": "<tipo_documento_esperado>",
            "document_type": "<tipo_do_documento_identificado>",
            "origem_entrega": "<origem_informada>",
            "is_valid": true | false,
            "observations": "coment\u00e1rios curtos ou "" "
            }

            Se n\u00e3o for poss\u00edvel identificar:

            {
            "document_expected": "<tipo_documento_esperado>",
            "document_type": "desconhecido",
            "origem_entrega": "<origem_informada>",
            "is_valid": false,
            "observations": "n\u00e3o foi poss\u00edvel identificar o documento"
            }

            Agora, sempre que receber um PDF ou imagem, devolva APENAS o JSON neste formato.

            """

# ---------------------------------------------------------------------------
# Regras gerais usadas na etapa de extra\u00e7\u00e3o
# ---------------------------------------------------------------------------
REGRAS_GERAIS_EXTRACAO: str = """
            REGRAS GERAIS:
            - Campos inexistentes, ileg\u00edveis ou duvidosos devem ser null.
            - Datas devem estar no formato "dd/mm/aaaa" quando poss\u00edvel.
            - N\u00e3o invente dados.
            - N\u00e3o traduza nem adapte textos.
            - Mantenha acentua\u00e7\u00e3o, nomes pr\u00f3prios e abrevia\u00e7\u00f5es como no documento.
            - N\u00e3o inclua qualquer texto fora do JSON.
            - N\u00e3o deve haver formata\u00e7\u00e3o para RG, CPF ou outros n\u00fameros (ex: pontos, tra\u00e7os, barras).

            FORMATO DO JSON:
            {
            "document_type": "<tipo>",
            "origem_entrega": "<origem>",
            "is_valid": true | false,
            "fields": { ... },
            "missing_mandatory_fields": ["campos obrigat\u00f3rios que ficaram null"],
            "observations": "coment\u00e1rios curtos ou \\"\\""
            }

            is_valid = true somente se TODOS os campos obrigat\u00f3rios forem preenchidos (n\u00e3o null).
            Responda APENAS com o JSON.
        """

# ---------------------------------------------------------------------------
# ETAPA 2: Prompts de extra\u00e7\u00e3o por tipo de documento
# ---------------------------------------------------------------------------
PROMPTS_EXTRACAO: Dict[str, str] = {
    "rg": """
                Extraia os dados deste RG (Registro Geral).

                fields:
                {
                "nome_pessoa": string | null,
                "rg": string | null,
                "nome_pai": string | null,
                "nome_mae": string | null,
                "orgao_emissor": string | null,
                "estado_emissor": string | null,
                "data_nascimento": "dd/mm/aaaa" | null,
                "data_emissao": "dd/mm/aaaa" | null,
                "cpf": string | null
                }

                Obrigat\u00f3rios: nome_pessoa, rg

                Regras especiais:
                - RG novo (n\u00famero \u00fanico RG = CPF):
                  Se houver apenas um n\u00famero rotulado como "RG/CPF", "Registro Geral - CPF" ou equivalente:
                  preencha rg e cpf com o MESMO n\u00famero. Registrar em observations.
                - Se o nome identificado for o que est\u00e1 acima da assinatura do diretor, O NOME EST\u00c1 ERRADO!
                - orgao_emissor deve conter APENAS a sigla (ex: SSP).
                - estado_emissor deve conter APENAS a sigla do estado (ex: SP, RJ, MG).
            """,

    "cpf": """
                Extraia os dados deste CPF.

                fields:
                {
                "nome_pessoa": string | null,
                "cpf": string | null,
                "data_nascimento": "dd/mm/aaaa" | null
                }

                Obrigat\u00f3rios: nome_pessoa, cpf
            """,

    "cnh": """
                Extraia os dados desta CNH.

                fields:
                {
                "nome_pessoa": string | null,
                "data_nascimento": "dd/mm/aaaa" | null,
                "rg": string | null,
                "cpf": string | null,
                "orgao_emissor": string | null,
                "nome_pai": string | null,
                "nome_mae": string | null,
                "data_emissao": "dd/mm/aaaa" | null
                }

                Obrigat\u00f3rios: nome_pessoa, data_nascimento, rg, cpf
            """,

    "certidao_nascimento": """
                Extraia os dados desta Certid\u00e3o de Nascimento.

                fields:
                {
                "nome_pessoa": string | null,
                "data_nascimento": "dd/mm/aaaa" | null,
                "nome_pai": string | null,
                "nome_mae": string | null,
                "sexo": string | null,
                "instituicao_nascimento": string | null,
                "cidade_nascimento": string | null,
                "estado_nascimento": string | null
                }

                Obrigat\u00f3rios: nome_pessoa, data_nascimento, cidade_nascimento, estado_nascimento

                Regras especiais:
                - instituicao_nascimento deve conter o nome do hospital, maternidade ou local de nascimento.
                - cidade_nascimento deve refletir APENAS a cidade conforme na certid\u00e3o.
                - estado_nascimento deve refletir APENAS o estado EM SIGLA (ex: SP, RJ).
            """,

    "certidao_casamento": """
                Extraia os dados desta Certid\u00e3o de Casamento / Uni\u00e3o Est\u00e1vel.

                fields:
                {
                "nome_noiva_pos_casamento": string | null,
                "nome_noivo_pos_casamento": string | null,
                "data_casamento": "dd/mm/aaaa" | null,
                "cpfs_conjuges": string[] | null
                }

                Obrigat\u00f3rios: nome_noiva_pos_casamento, nome_noivo_pos_casamento, data_casamento
            """,

    "comprovante_residencia": """
                Extraia os dados deste Comprovante de Resid\u00eancia.
                Aceita qualquer documento que contenha nome, endere\u00e7o e CEP
                (contas banc\u00e1rias, contas de consumo, contratos, comunicados oficiais).

                fields:
                {
                "nome_pessoa": string | null,
                "endereco": string | null,
                "cep": string | null
                }

                Obrigat\u00f3rios: nome_pessoa, endereco, cep
            """,

    "titulo_eleitor": """
                Extraia os dados deste T\u00edtulo de Eleitor.

                fields:
                {
                "nome_pessoa": string | null,
                "data_nascimento": "dd/mm/aaaa" | null,
                "municipio": string | null,
                "estado": string | null,
                "nome_pai": string | null,
                "nome_mae": string | null,
                "zona": string | null,
                "secao": string | null,
                "data_emissao": "dd/mm/aaaa" | null,
                "numero_titulo": string | null
                }

                Obrigat\u00f3rios: nome_pessoa, data_nascimento, municipio, estado, zona, secao, data_emissao, numero_titulo
            """,

    "certificado_reservista": """
                Extraia os dados deste Certificado de Reservista.

                fields:
                {
                "ra": string | null,
                "nome_pessoa": string | null,
                "nome_pai": string | null,
                "nome_mae": string | null,
                "data_nascimento": "dd/mm/aaaa" | null,
                "municipio_nascimento": string | null,
                "cpf": string | null,
                "rm": string | null,
                "serie": string | null
                }

                Obrigat\u00f3rios: ra, nome_pessoa, cpf
            """,

    "conclusao_historico": """
                Extraia os dados deste documento de Conclus\u00e3o / Hist\u00f3rico Escolar.

                fields:
                {
                "nome_pessoa": string | null,
                "nivel_ensino": "ensino_fundamental" | "ensino_medio" | "ensino_superior" | null,
                "historico": {
                    "instituicao_ensino": string | null,
                    "disciplinas": [] | null
                },
                "conclusao": {
                    "ano_conclusao": "YYYY" | null,
                    "instituicao_ensino": string | null
                }
                }

                Regras RIGOROSAS DE VALIDA\u00c7\u00c3O POR ORIGEM:
                - Se a origem for "escola": REJEITAR se n\u00edvel_ensino != "ensino_fundamental"
                - Se a origem for "graduacao": REJEITAR se n\u00edvel_ensino != "ensino_medio" (n\u00e3o aceitar Fundamental nem Superior)
                - Se a origem for "pos_graduacao": REJEITAR se n\u00edvel_ensino != "ensino_superior"
                
                Identifica\u00e7\u00e3o de n\u00edveis:
                - "Ensino Superior", "Gradua\u00e7\u00e3o", "Faculdade", "Universidade", "3\u00ba grau" \u2192 ensino_superior
                - "Ensino M\u00e9dio", "2\u00ba grau", "colegial" \u2192 ensino_medio
                - "Ensino Fundamental", "1\u00ba grau" \u2192 ensino_fundamental

                Obrigat\u00f3rios: nome_pessoa, conclusao.ano_conclusao, conclusao.instituicao_ensino
            """,

    "certificado_conclusao_ensino_medio": """
                Extraia os dados deste documento de Conclus\u00e3o / Hist\u00f3rico Escolar (Ensino M\u00e9dio).

                fields:
                {
                "nome_pessoa": string | null,
                "nivel_ensino": "ensino_medio" | null,
                "historico": {
                    "instituicao_ensino": string | null,
                    "disciplinas": [] | null
                },
                "conclusao": {
                    "ano_conclusao": "YYYY" | null,
                    "instituicao_ensino": string | null
                }
                }

                Regras:
                - Este \u00e9 SEMPRE Ensino M\u00e9dio. Marcar nivel_ensino = "ensino_medio".
                - Se a origem for "graduacao", aceitar (Ensino M\u00e9dio \u00e9 exigido).
                - Rejeitar para outras origens.

                Obrigat\u00f3rios: nome_pessoa, conclusao.ano_conclusao, conclusao.instituicao_ensino
            """,

    "historico_escolar_fundamental": """
                Extraia os dados deste documento de Conclus\u00e3o / Hist\u00f3rico Escolar (Ensino Fundamental).

                fields:
                {
                "nome_pessoa": string | null,
                "nivel_ensino": "ensino_fundamental" | null,
                "historico": {
                    "instituicao_ensino": string | null,
                    "disciplinas": [] | null
                },
                "conclusao": {
                    "ano_conclusao": "YYYY" | null,
                    "instituicao_ensino": string | null
                }
                }

                Regras:
                - Este \u00e9 SEMPRE Ensino Fundamental. Marcar nivel_ensino = "ensino_fundamental".
                - Se a origem for "escola", aceitar (Ensino Fundamental \u00e9 exigido).
                - Rejeitar para outras origens.

                Obrigat\u00f3rios: nome_pessoa, conclusao.ano_conclusao, conclusao.instituicao_ensino
            """,

    "certificado_diploma_graduacao": """
                Extraia os dados deste Certificado ou Diploma de Graduação (Ensino Superior).
                fields:
                {
                "nome_pessoa": string | null,
                "nivel_ensino": "ensino_superior" | null,
                "historico": {
                    "instituicao_ensino": string | null,
                    "disciplinas": [] | null
                },
                "conclusao": {
                    "ano_conclusao": "YYYY" | null,
                    "instituicao_ensino": string | null
                }
                }
                Regras:
                - Este é SEMPRE Ensino Superior. Marcar nivel_ensino = "ensino_superior".
                - Se a origem for "pos_graduacao", aceitar (Ensino Superior é exigido).
                - Rejeitar para outras origens.
                
                Obrigatórios: nome_pessoa, conclusao.ano_conclusao, conclusao.instituicao_ensino
            """,

    "declaracao_transferencia": """
                Extraia os dados desta Declara\u00e7\u00e3o de Transfer\u00eancia.

                fields:
                {
                "nome_pessoa": string | null,
                "instituicao_origem": string | null,
                "data_emissao": "dd/mm/aaaa" | null,
                "cidade": string | null,
                "estado": string | null
                }

                Regras:
                - "instituicao_origem" \u00e9 a escola de onde o aluno est\u00e1 saindo.
                - "cidade" e "estado" devem refletir o local de emiss\u00e3o (ex.: "S\u00e3o Paulo - SP").

                Obrigat\u00f3rios: nome_pessoa, instituicao_origem, data_emissao
            """,

    "carteira_vacinacao": """
                Extraia os dados desta Carteira de Vacina\u00e7\u00e3o.

                fields:
                {
                "nome_pessoa": string | null,
                "data_nascimento": "dd/mm/aaaa" | null,
                "numero_cadastro": string | null
                }
            """,
}


# ===========================================================================
# Classe principal
# ===========================================================================
class GeminiDocumentos:
    """Analisa documentos brasileiros via Gemini (valida\u00e7\u00e3o + extra\u00e7\u00e3o)."""

    def __init__(self) -> None:
        self.client: genai.Client = genai.Client(api_key=GEMINI_API_KEY_PRIMARY)

    # -----------------------------------------------------------------------
    # M\u00e9todo p\u00fablico (snake_case)
    # -----------------------------------------------------------------------
    def analisar_documento(
        self,
        url: str,
        origem: str,
        tipo_doc: str = "",
    ) -> Dict[str, Any]:
        """Ponto de entrada: baixa o arquivo, identifica e extrai dados."""
        ext = url.lower().rsplit(".", maxsplit=1)[-1]

        if ext == "docx":
            return self._docx_to_pdf_from_url(url, origem, tipo_doc=tipo_doc)

        mime_type = MIME_TYPES.get(ext)
        if mime_type is None:
            return {"Erro": True, "Motivo": "Tipo de arquivo n\u00e3o suportado"}

        try:
            doc_bytes = baixar_arquivo(url)
        except Exception as e:
            return {"Erro": True, "Motivo": str(e)}

        return self._processar_duas_etapas(doc_bytes, mime_type, origem, tipo_doc)

    # Retrocompatibilidade camelCase
    analisarDocumento = analisar_documento

    # -----------------------------------------------------------------------
    # Pipeline de duas etapas (valida\u00e7\u00e3o + extra\u00e7\u00e3o)
    # -----------------------------------------------------------------------
    def _processar_duas_etapas(
        self,
        doc_bytes: bytes,
        mime_type: str,
        origem: str,
        tipo_doc: str = "",
    ) -> Dict[str, Any]:
        retorno: Dict[str, Any] = {}

        # -- Etapa 1: Identifica\u00e7\u00e3o e Valida\u00e7\u00e3o --
        try:
            prompt_val = (
                PROMPT_VALIDACAO
                + f"O tipo de documento esperado \u00e9: {tipo_doc}\n"
                + f"A origem da entrega informada \u00e9: {origem}"
            )
            response_val = self.client.models.generate_content(
                model=MODELO_VALIDACAO,
                contents=[
                    types.Part.from_bytes(data=doc_bytes, mime_type=mime_type),
                    prompt_val,
                ],
            )
            retorno["validacao"] = safe_json_load(response_val.text)
        except Exception as e:
            return {"Erro": True, "Motivo": str(e)}

        # Se inv\u00e1lido, retorna sem extrair
        if not retorno["validacao"].get("is_valid"):
            return retorno

        # -- Etapa 2: Extra\u00e7\u00e3o de Dados --
        doc_type: str = retorno["validacao"].get("document_type", "desconhecido")
        prompt_extracao = PROMPTS_EXTRACAO.get(doc_type)

        if not prompt_extracao:
            retorno["extracao"] = {
                "document_type": doc_type,
                "origem_entrega": origem,
                "is_valid": False,
                "fields": {},
                "missing_mandatory_fields": ["tipo_documento"],
                "observations": f"Tipo '{doc_type}' n\u00e3o possui prompt de extra\u00e7\u00e3o",
            }
            return retorno

        try:
            prompt_completo = (
                f"Voc\u00ea \u00e9 um extrator de dados de documentos brasileiros.\n"
                f"O documento \u00e9 do tipo: {doc_type}\n"
                f"A origem da entrega \u00e9: {origem}\n\n"
                f"{prompt_extracao}\n\n"
                f"{REGRAS_GERAIS_EXTRACAO}"
            )

            response_ext = self.client.models.generate_content(
                model=MODELO_EXTRACAO,
                contents=[
                    types.Part.from_bytes(data=doc_bytes, mime_type=mime_type),
                    prompt_completo,
                ],
            )
            retorno["extracao"] = safe_json_load(response_ext.text)
        except Exception as e:
            retorno["extracao"] = {"Erro": True, "Motivo": str(e)}

        return retorno

    # -----------------------------------------------------------------------
    # Convers\u00e3o DOCX -> PDF via LibreOffice
    # -----------------------------------------------------------------------
    def _docx_to_pdf_from_url(
        self,
        url: str,
        origem: str,
        tipo_doc: str = "",
        pdf_name: Optional[str] = "DocumentoTransformado.pdf",
    ) -> Dict[str, Any]:
        project_dir = os.getcwd()
        safe_origem = str(origem).replace(" ", "_") if origem else "origem"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_id = f"{safe_origem}_{timestamp}"

        if pdf_name is None:
            pdf_name = f"{safe_origem}_{timestamp}.pdf"

        docx_path = os.path.join(project_dir, f"{file_id}.docx")
        pdf_path = os.path.join(project_dir, pdf_name)

        # Baixar DOCX usando utilit\u00e1rio compartilhado
        try:
            docx_bytes = baixar_arquivo(url)
        except Exception as e:
            return {"Erro": True, "Motivo": str(e)}

        with open(docx_path, "wb") as f:
            f.write(docx_bytes)

        try:
            libreoffice_path = os.getenv(
                "LIBREOFFICE_PATH",
                r"C:\Program Files\LibreOffice\program\soffice.exe",
            )

            subprocess.run(
                [
                    libreoffice_path,
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", project_dir,
                    docx_path,
                ],
                check=True,
            )

            generated_pdf = docx_path.replace(".docx", ".pdf")
            os.rename(generated_pdf, pdf_path)

            with open(pdf_path, "rb") as pf:
                pdf_bytes = pf.read()

            result = self._processar_duas_etapas(
                pdf_bytes, "application/pdf", origem, tipo_doc
            )

        except Exception as e:
            result = {"Erro": True, "Motivo": str(e)}

        finally:
            for path in (docx_path, pdf_path):
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except Exception:
                    pass

        return result

    # Retrocompatibilidade do m\u00e9todo antigo
    docx_to_pdf_from_url_word = _docx_to_pdf_from_url


# ---------------------------------------------------------------------------
# Alias para retrocompatibilidade
# ---------------------------------------------------------------------------
Gemini = GeminiDocumentos
