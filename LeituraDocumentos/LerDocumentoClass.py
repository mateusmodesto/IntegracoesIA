from datetime import datetime
import subprocess
from dotenv import load_dotenv
from google import genai
from google.genai import types
from langsmith import wrappers
import httpx
import requests
import os
import json

load_dotenv(os.path.join(os.path.dirname(__file__), "config.env"))

class Gemini():
    def __init__(self):
        self.gemini_client = genai.Client()
        self.client = wrappers.wrap_gemini(self.gemini_client,tracing_extra={
            "tags": ["gemini", "python"],
            "metadata": {
                "integration": "google-genai",
            },
        },)

        # ── ETAPA 1: Identificação e Validação ──
        self.prompt_validacao = """
            Você é um identificador de documentos brasileiros a partir de PDFs e imagens.

            Sua tarefa é:
            1. Ler o arquivo (PDF ou imagem) recebido.
            2. Identificar qual é o tipo de documento.
            3. Comparar o documento identificado com o tipo de documento esperado (informado externamente).
            4. Aplicar as regras de substituição para verificar se o documento é aceito.
            5. Verificar se o tipo de documento é aceito para a origem da entrega informada.
            6. Responder SEMPRE com um único objeto JSON, sem qualquer texto extra.

            --------------------------------
            VALIDAÇÃO POR ORIGEM
            --------------------------------

            origem_entrega = "pos_graduacao":
            Aceitar:
            - rg, cpf, cnh, certidao_nascimento, certidao_casamento, comprovante_residencia
            - conclusao_historico (graduação ou superior)

            origem_entrega = "graduacao":
            Aceitar:
            - rg, cpf, cnh, certidao_nascimento, certidao_casamento, comprovante_residencia
            - certificado_reservista, titulo_eleitor
            - conclusao_historico (**Apenas** Ensino Médio)

            origem_entrega = "escola":
            Aceitar:
            - rg, cpf, cnh, certidao_nascimento, certidao_casamento, comprovante_residencia
            - carteira_vacinacao, declaracao_transferencia
            - conclusao_historico (**Apenas** Ensino Fundamental)

            --------------------------------
            REGRAS DE SUBSTITUIÇÃO
            --------------------------------

            - CNH pode ser entregue no lugar do RG ou do CPF (is_valid = true).
            - RG pode ser entregue no lugar do CPF (is_valid = true).
            - CPF NÃO pode ser entregue no lugar do RG (is_valid = false).

            --------------------------------
            REGRAS
            --------------------------------

            - NÃO tente inferir a origem a partir do conteúdo do documento.
            - Apenas utilize a origem informada para validar se o documento é aceito ou não.
            - Para conclusao_historico, identifique o nível de ensino (fundamental/medio/superior) e valide conforme a origem.
            - Se não for possível identificar o documento, use "desconhecido".

            --------------------------------
            FORMATO DO JSON
            --------------------------------

            {
            "document_expected": "<tipo_documento_esperado>",
            "document_type": "<tipo_do_documento_identificado>",
            "origem_entrega": "<origem_informada>",
            "is_valid": true | false,
            "observations": "comentários curtos ou \\"\\""
            }

            Se não for possível identificar:
            {
            "document_expected": "<tipo_documento_esperado>",
            "document_type": "desconhecido",
            "origem_entrega": "<origem_informada>",
            "is_valid": false,
            "observations": "não foi possível identificar o documento"
            }

            Agora, sempre que receber um PDF ou imagem, devolva APENAS o JSON neste formato.
            """

        # ── ETAPA 2: Prompts de extração por tipo de documento ──
        self._regras_gerais = """
            REGRAS GERAIS:
            - Campos inexistentes, ilegíveis ou duvidosos devem ser null.
            - Datas devem estar no formato "dd/mm/aaaa" quando possível.
            - Não invente dados.
            - Não traduza nem adapte textos.
            - Mantenha acentuação, nomes próprios e abreviações como no documento.
            - Não inclua qualquer texto fora do JSON.
            - Não deve haver formatação para RG, CPF ou outros números (ex: pontos, traços, barras).

            FORMATO DO JSON:
            {
            "document_type": "<tipo>",
            "origem_entrega": "<origem>",
            "is_valid": true | false,
            "fields": { ... },
            "missing_mandatory_fields": ["campos obrigatórios que ficaram null"],
            "observations": "comentários curtos ou \\"\\""
            }

            is_valid = true somente se TODOS os campos obrigatórios forem preenchidos (não null).
            Responda APENAS com o JSON.
        """

        self.prompts_extracao = {
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

                Obrigatórios: nome_pessoa, rg

                Regras especiais:
                - RG novo (número único RG = CPF):
                  Se houver apenas um número rotulado como "RG/CPF", "Registro Geral - CPF" ou equivalente:
                  preencha rg e cpf com o MESMO número. Registrar em observations.
                - Se o nome identificado for o que está acima da assinatura do diretor, O NOME ESTÁ ERRADO!
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

                Obrigatórios: nome_pessoa, cpf
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

                Obrigatórios: nome_pessoa, data_nascimento, rg, cpf
            """,

            "certidao_nascimento": """
                Extraia os dados desta Certidão de Nascimento.

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

                Obrigatórios: nome_pessoa, data_nascimento, cidade_nascimento, estado_nascimento

                Regras especiais:
                - instituicao_nascimento deve conter o nome do hospital, maternidade ou local de nascimento.
                - cidade_nascimento deve refletir APENAS a cidade conforme na certidão.
                - estado_nascimento deve refletir APENAS o estado EM SIGLA (ex: SP, RJ).
            """,

            "certidao_casamento": """
                Extraia os dados desta Certidão de Casamento / União Estável.

                fields:
                {
                "nome_noiva_pos_casamento": string | null,
                "nome_noivo_pos_casamento": string | null,
                "data_casamento": "dd/mm/aaaa" | null,
                "cpfs_conjuges": string[] | null
                }

                Obrigatórios: nome_noiva_pos_casamento, nome_noivo_pos_casamento, data_casamento
            """,

            "comprovante_residencia": """
                Extraia os dados deste Comprovante de Residência.
                Aceita qualquer documento que contenha nome, endereço e CEP
                (contas bancárias, contas de consumo, contratos, comunicados oficiais).

                fields:
                {
                "nome_pessoa": string | null,
                "endereco": string | null,
                "cep": string | null
                }

                Obrigatórios: nome_pessoa, endereco, cep
            """,

            "titulo_eleitor": """
                Extraia os dados deste Título de Eleitor.

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

                Obrigatórios: nome_pessoa, data_nascimento, municipio, estado, zona, secao, data_emissao, numero_titulo
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

                Obrigatórios: ra, nome_pessoa, cpf
            """,

            "conclusao_historico": """
                Extraia os dados deste documento de Conclusão / Histórico Escolar.

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

                Regras:
                - Ensino superior implica automaticamente conclusão do Ensino Médio.
                - Termos como "2º grau" indicam Ensino Médio.
                - Se a origem for "escola", aceitar apenas Ensino Fundamental.
                - Se a origem for "graduacao", aceitar apenas Ensino Médio.
                - Se a origem for "pos_graduacao", aceitar apenas Ensino Superior.

                Obrigatórios: nome_pessoa, conclusao.ano_conclusao, conclusao.instituicao_ensino
            """,

            "declaracao_transferencia": """
                Extraia os dados desta Declaração de Transferência.

                fields:
                {
                "nome_pessoa": string | null,
                "instituicao_origem": string | null,
                "data_emissao": "dd/mm/aaaa" | null,
                "cidade": string | null,
                "estado": string | null
                }

                Regras:
                - "instituicao_origem" é a escola de onde o aluno está saindo.
                - "cidade" e "estado" devem refletir o local de emissão (ex.: "São Paulo - SP").

                Obrigatórios: nome_pessoa, instituicao_origem, data_emissao
            """,

            "carteira_vacinacao": """
                Extraia os dados desta Carteira de Vacinação.

                fields:
                {
                "nome_pessoa": string | null,
                "data_nascimento": "dd/mm/aaaa" | null,
                "numero_cadastro": string | null
                }
            """,
        }

    def analisarDocumento(self, url, origem, tipo_doc=''):
        ext = url.lower().split(".")[-1]

        if ext in ["jpg", "jpeg", "png", "tiff"]:
            mime_type = "image/jpeg"
        elif ext == "pdf":
            mime_type = "application/pdf"
        elif ext == "docx":
            return self.docx_to_pdf_from_url_word(url, origem, tipo_doc=tipo_doc)
        else:
            return {"Erro": True, "Motivo": "Tipo de arquivo não suportado"}

        try:
            doc_bytes = self._baixar_arquivo(url)
        except Exception as e:
            return {"Erro": True, "Motivo": str(e)}

        return self._processar_duas_etapas(doc_bytes, mime_type, origem, tipo_doc)

    def _baixar_arquivo(self, url):
        if url.startswith("http"):
            return httpx.get(url, timeout=60).content
        with open(url, "rb") as f:
            return f.read()

    def _processar_duas_etapas(self, doc_bytes, mime_type, origem, tipo_doc=''):
        retorno = {}

        # ── Etapa 1: Identificação e Validação ──
        try:
            prompt_val = (
                self.prompt_validacao
                + f"O tipo de documento esperado é: {tipo_doc}\n"
                + f"A origem da entrega informada é: {origem}"
            )
            response_val = self.client.models.generate_content(
                model='gemini-2.5-flash-lite',
                contents=[
                    types.Part.from_bytes(
                        data=doc_bytes,
                        mime_type=mime_type,
                    ),
                    prompt_val
                ]
            )
            retorno['validacao'] = self._safe_json_load(response_val.text)
        except Exception as e:
            return {"Erro": True, "Motivo": str(e)}

        # Se inválido, retorna sem extrair
        if not retorno['validacao'].get('is_valid'):
            return retorno

        # ── Etapa 2: Extração de Dados ──
        doc_type = retorno['validacao'].get('document_type', 'desconhecido')
        prompt_extracao = self.prompts_extracao.get(doc_type)

        if not prompt_extracao:
            retorno['extracao'] = {
                "document_type": doc_type,
                "origem_entrega": origem,
                "is_valid": False,
                "fields": {},
                "missing_mandatory_fields": ["tipo_documento"],
                "observations": f"Tipo '{doc_type}' não possui prompt de extração"
            }
            return retorno

        try:
            prompt_completo = (
                f"Você é um extrator de dados de documentos brasileiros.\n"
                f"O documento é do tipo: {doc_type}\n"
                f"A origem da entrega é: {origem}\n\n"
                f"{prompt_extracao}\n\n"
                f"{self._regras_gerais}"
            )

            response_ext = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    types.Part.from_bytes(
                        data=doc_bytes,
                        mime_type=mime_type,
                    ),
                    prompt_completo
                ]
            )
            retorno['extracao'] = self._safe_json_load(response_ext.text)
        except Exception as e:
            retorno['extracao'] = {"Erro": True, "Motivo": str(e)}

        return retorno

    def docx_to_pdf_from_url_word(self, url, origem, tipo_doc='', pdf_name='DocumentoTransformado.pdf'):
        project_dir = os.getcwd()
        safe_origem = str(origem).replace(' ', '_') if origem else 'origem'

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_id = f"{safe_origem}_{timestamp}"

        if pdf_name is None:
            pdf_name = f"{safe_origem}_{timestamp}.pdf"

        docx_path = os.path.join(project_dir, f"{file_id}.docx")
        pdf_path = os.path.join(project_dir, pdf_name)

        # baixar DOCX
        r = requests.get(url)
        r.raise_for_status()
        with open(docx_path, "wb") as f:
            f.write(r.content)

        try:
            libreoffice_path = "C:\\Program Files\\LibreOffice\\program\\soffice.exe"

            subprocess.run(
                [
                    libreoffice_path,
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", project_dir,
                    docx_path
                ],
                check=True
            )

            generated_pdf = docx_path.replace(".docx", ".pdf")
            os.rename(generated_pdf, pdf_path)

            with open(pdf_path, "rb") as pf:
                pdf_bytes = pf.read()

            result = self._processar_duas_etapas(pdf_bytes, 'application/pdf', origem, tipo_doc)

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

    def _safe_json_load(self, text):
        if not text or not isinstance(text, str):
            raise ValueError("Resposta vazia ou inválida da IA")

        cleaned = text.strip()
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()

        decoder = json.JSONDecoder()

        for start in range(len(cleaned)):
            if cleaned[start] in "{[":
                try:
                    obj, idx = decoder.raw_decode(cleaned[start:])
                    return obj
                except json.JSONDecodeError:
                    continue

        raise ValueError(
            "Resposta da IA não contém JSON válido.\n"
            f"Conteúdo recebido:\n{cleaned[:1000]}"
        )
