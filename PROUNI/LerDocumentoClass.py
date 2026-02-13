from datetime import datetime
import subprocess
from dotenv import load_dotenv
from google import genai
from google.genai import types
import httpx
from langsmith import wrappers
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
        
        self.prompt_valida = """
            Você é um extrator de dados de documentos brasileiros a partir de PDFs e imagens (scans de documentos físicos).

            Sua tarefa é:
            1. Ler o arquivo (PDF ou imagem) recebido.
            2. Identificar qual é o tipo de documento.
            3. Comparar para ver se realmente bate com o tipo de documento informado no campo "tipo_documento" (ex: RG, CPF, CNH, etc).
            4. Retornar o JSON com as informações extraídas.

            --------------------------------
            FORMATO GERAL DO JSON
            --------------------------------

            {
            "document_informado": "<tipo_documento_informado>",
            "document_type": "<tipo_do_documento>",
            "is_valid": true | false,
            "observations": "comentários curtos ou \"\" se nada a observar"
            }

            --------------------------------
            Se não for possível identificar o documento:
            --------------------------------          

            {
            "document_type": "desconhecido",
            "document_informado": "<tipo_documento_informado>",
            "is_valid": false,
            "observations": "não foi possível identificar o documento"
            }

            Agora, sempre que receber um PDF ou imagem, devolva APENAS o JSON neste formato. 

            """
        
        self.prompt_documentos = {
            'CPF': """
            --------------------------------
            REGRAS DE VALIDAÇÃO
            --------------------------------
            1. Se o documento informado for CPF e o documento identificado for RG OU CNH, então is_valid = true.
            """,
            'RG': """
            --------------------------------
            REGRAS DE VALIDAÇÃO
            --------------------------------
            1. Se o documento informado for RG e o documento identificado for CNH, então is_valid = true.            
            """,
            'HISTORICO_ESCOLAR': """
            --------------------------------
            REGRAS DE VALIDAÇÃO
            --------------------------------
            1. Se o documento informado for Histórico Escolar do Ensino Médio ou Certificado de Conclusão de Ensino Médio e o documento identificado for de algum outro tipo de documento escolar, então is_valid = false. Deve aceitar apenas do ensino médio. 
            """,
            'Declaracao de auxilio financeiro': """
            --------------------------------
            REGRAS DE VALIDAÇÃO
            --------------------------------
            1. Se o documento informado for "Declaração de Auxílio Financeiro", considere válido (is_valid=true) qualquer documento que traga evidência explícita de recebimento de auxílio/benefício/renda externa (ex.: Bolsa Família/Auxílio Brasil, INSS/aposentadoria/pensão/BPC, seguro-desemprego/seguro, pensão alimentícia ou crédito bancário identificado como benefício). Se não houver essa evidência explícita, is_valid=false.
            """,
            'CTPS - Qualificacao Civil': """
            --------------------------------
            REGRAS DE VALIDAÇÃO
            --------------------------------
            """,
            'CTPS - Pagina Em Branco': """
            --------------------------------
            REGRAS DE VALIDAÇÃO
            --------------------------------
            1. Se o documento informado for CTPS - Página em Branco, o documento só deverá ser considerado válido se for uma página de contrato de trabalho em branco da CTPS.
            """,
            'CTPS - Ultimo Contrato': """
            --------------------------------
            REGRAS DE VALIDAÇÃO
            --------------------------------
            1. Se o documento informado for CTPS - Último Contrato, o documento só deverá ser considerado válido se for uma página de contrato de trabalho da CTPS.
            """,
            'declaracao de renda': """
            --------------------------------
            REGRAS DE VALIDAÇÃO
            --------------------------------
            1. Se o documento informado for "Declaração de Renda", considere válido (is_valid=true) qualquer documento que mostre de forma explícita uma renda/entrada de dinheiro (valor e/ou periodicidade), como holerite/contracheque, extrato bancário com créditos identificados, declaração de rendimentos, comprovante de aposentadoria/pensão/benefício, recibo de pagamento ou contrato/declaração que informe valor de remuneração. Se não houver evidência explícita de renda, is_valid=false.
            """,
            'pro-labore': """
            --------------------------------
            REGRAS DE VALIDAÇÃO
            --------------------------------
            1. Se o documento informado for "Pró-labore", considere válido (is_valid=true) qualquer documento que indique explicitamente pagamento de pró-labore ao titular (ex.: demonstrativo/recibo de pró-labore, holerite com “pró-labore”, extrato com crédito identificado como pró-labore ou declaração/contábil da empresa informando o valor). Se não houver menção explícita a pró-labore ou pagamento equivalente ao sócio/administrador, is_valid=false.
            """
        }
        self.prompt_extrair = """

        """

    def analisarDocumento(self, url, tipo_doc):
        retorno = {}
        ext = url.lower().split(".")[-1]
        if ext in ["jpg", "jpeg", "png", "tiff"]:
            retorno['validacao'] = self.lerDocumento(url, tipo_doc, 'image/jpeg', 'validacao')
            if retorno['validacao'].get("is_valid") == True:
                retorno['extracao'] = self.lerDocumento(url, tipo_doc, 'image/jpeg', 'extracao')
            return retorno
        elif ext == "pdf":
            retorno['validacao'] = self.lerDocumento(url, tipo_doc, 'application/pdf', 'validacao')
            if retorno['validacao'].get("is_valid") == True:
                retorno['extracao'] = self.lerDocumento(url, tipo_doc, 'application/pdf', 'extracao')
            return retorno
        elif ext == 'docx':
            return self.docx_to_pdf_from_url_word(url, tipo_doc)
            
        else:
            return {"Erro": True, "Motivo": "Tipo de arquivo não suportado"}
        
    def lerDocumento(self, url, tipo_doc, metodo, tipo_prompt):
        
        try:
            if url.startswith("http"):
                doc_data = httpx.get(url, timeout=60).content
            else:
                with open(url, "rb") as f:
                    doc_data = f.read()
            if tipo_prompt == 'validacao':
                self.prompt_valida += self.prompt_documentos.get(tipo_doc, "")
                response_validacao = self.client.models.generate_content(
                    model='gemini-2.5-flash-lite',
                    contents=[
                        types.Part.from_bytes(
                            data=doc_data,
                            mime_type=metodo,
                        ),
                        self.prompt_valida + f"O tipo de documento informado é: {tipo_doc}"
                    ]
                )
                return self._safe_json_load(response_validacao.text)
            
            elif tipo_prompt == 'extracao':

                if tipo_doc == 'holerite':

                    response_extracao = self.client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=[
                            types.Part.from_bytes(
                                data=doc_data,
                                mime_type=metodo,
                            ),
                            """
                                Você é um extrator de dados de holerites brasileiros a partir de PDFs e imagens (scans de documentos físicos).

                                Sua tarefa é extrair as seguintes informações do holerite:
                                    - Salário
                                    - Adicionais 
                                    - Salário Bruto
                                    - Salário Líquido
                                    - Descontos

                                Retorne um JSON com as informações extraídas, seguindo este formato:
                                {   
                                    "salario": "valor ou null",
                                    "adicionais": {
                                        "tipo_do_adicional": "valor do adicional",                                       
                                        "tipo_do_adicional": "valor do adicional"
                                    },
                                    "salario_bruto": "valor ou null",
                                    "salario_liquido": "valor ou null",
                                    "descontos": {
                                        "tipo_do_desconto": "valor do desconto",                                       
                                        "tipo_do_desconto": "valor do desconto"
                                    },
                                    "observations": "comentários curtos ou \"\" se nada a observar"
                                }
                            """
                      ]
                    )
                    return self._safe_json_load(response_extracao.text)

        except Exception as e:
            return {"Erro": True, "Motivo": str(e)}
        
    def docx_to_pdf_from_url_word(self, url, tipo_doc, pdf_name='DocumentoTransformado.pdf'):
        retorno = {}
        project_dir = os.getcwd()
        safe_tipo_doc = str(tipo_doc).replace(' ', '_') if tipo_doc else 'tipo_documento'
        
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        file_id = f"{safe_tipo_doc}_{timestamp}"

        if pdf_name is None:
            pdf_name = f"{safe_tipo_doc}_{timestamp}.pdf"

        docx_path = os.path.join(project_dir, f"{file_id}.docx")
        pdf_path = os.path.join(project_dir, pdf_name)

        # baixar DOCX
        r = requests.get(url)
        r.raise_for_status()
        with open(docx_path, "wb") as f:
            f.write(r.content)

        try:
            libreoffice_path = "C:\\Program Files\\LibreOffice\\program\\soffice.exe"

            # converter via LibreOffice headless
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

            # LibreOffice gera PDF com o mesmo nome base
            generated_pdf = docx_path.replace(".docx", ".pdf")
            os.rename(generated_pdf, pdf_path)

            with open(pdf_path, "rb") as pf:
                pdf_bytes = pf.read()

            response = self.lerDocumento(pdf_path, tipo_doc, 'application/pdf', 'validacao')
            retorno['validacao'] = response

            response_validacao = self._safe_json_load(response.text)
            if response_validacao.get("is_valid") == True:
                response_extracao = self.lerDocumento(pdf_path, tipo_doc, 'application/pdf', 'extracao')
                retorno['extracao'] = self._safe_json_load(response_extracao.text)
            else:
                retorno['extracao'] = {"Erro": True, "Motivo": "Documento inválido"}

        except Exception as e:
            retorno['Erro'] = True
            retorno['Motivo'] = str(e)

        finally:
            for path in (docx_path, pdf_path):
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except Exception:
                    pass

        return retorno

    def _safe_json_load(self, text: str):
        if not text or not isinstance(text, str):
            raise ValueError("Resposta vazia ou inválida da IA")

        cleaned = text.strip()
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()

        decoder = json.JSONDecoder()

        # tenta decodificar a partir do primeiro { ou [
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

