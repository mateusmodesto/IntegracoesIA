import json
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from google import genai
from google.genai import types

from shared.config import GEMINI_API_KEY_PRIMARY
from shared.gemini_helpers import safe_json_load, baixar_arquivo

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

MODELO = "gemini-2.5-flash"

GEN_CONFIG = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_budget=1024),
    temperature=0.2,
    response_mime_type="application/json",
)

MIME_TYPES: Dict[str, str] = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".tiff": "image/tiff",
}

EXTENSOES_SUPORTADAS = set(MIME_TYPES.keys())

PROMPT_COMPARACAO = (
    "Compare disciplinas cursadas (historico) x novas (grade). Retorne JSON.\n"
    "\n"
    "IDIOMA: O historico pode estar em QUALQUER idioma (portugues, ingles, espanhol, etc). "
    "Traduza mentalmente os nomes das disciplinas para portugues antes de comparar. "
    "Ex: 'Calculus I'='Calculo I', 'Introduction to Computing'='Introducao a Computacao', "
    "'General Chemistry'='Quimica Geral', 'Physics I'='Fisica I'.\n"
    "\n"
    "REGRA PRINCIPAL - COMPARACAO POR NOME:\n"
    "A equivalencia e determinada EXCLUSIVAMENTE pelo nome da disciplina.\n"
    "Normalizar antes de comparar: traduzir para portugues, minusculas, sem acentos, sem pontuacao, espacos unicos.\n"
    "Considerar equivalente quando:\n"
    "- Nomes IDENTICOS apos normalizacao, OU\n"
    "- Nomes PARECIDOS: um contem o outro (minimo 6 chars), OU\n"
    "- Nomes SIMILARES: >= 75%% das palavras da nova disciplina aparecem no nome do historico, OU\n"
    "- SIGNIFICADO EQUIVALENTE: nomes diferentes mas que representam a mesma disciplina academica. "
    "Usar conhecimento academico para identificar sinonimos e equivalencias semanticas "
    "(ex: 'Calculo Diferencial'~'Calculo I', 'Introducao a Computacao'~'Fundamentos de Informatica', "
    "'Lingua Portuguesa'~'Comunicacao e Expressao', 'Metodologia Cientifica'~'Metodos de Pesquisa').\n"
    "IMPORTANTE: codigos de disciplina (ex: 'CMPS 131','MAT 201') NAO sao nomes. "
    "NAO usar codigos, carga horaria ou outros campos para determinar equivalencia. "
    "Se o historico so tem codigo sem nome descritivo, essa disciplina NAO pode ser considerada equivalente.\n"
    "\n"
    "NUMERACAO: sufixo final (I-X ou 1-9) = numeral; resto = base_name. Manter 'modulo','parte','nivel','turma'.\n"
    "A(nova TEM numeral): A1)mesmo base+numeral->direto; A2)base sem numeral->generica; "
    "A3)outros numerais->agrupa,obs:'Nova=NUM;historico cobre ate NUM_MAX'; A4)nada->nao dispensa\n"
    "B(nova SEM numeral): B1)1 disciplina->direto; B2)multiplas numeradas->agrupa; "
    "B3)generica+numeradas->prefere generica valida, senao agrupa\n"
    "\n"
    "SITUACAO VALIDA PARA DISPENSA: APROVADO(AP,APR,APROVADO,APROVADA,APROV,DEFERIDO,DEFERIDA,APTO,APTA,AF,SAT), "
    "DISPENSADO(DISPENSADO,DISPENSA,EQUIVALENCIA,APROVEITAMENTO,DP). "
    "Equivalentes em ingles: PASS,PASSED,APPROVED,CREDIT,TRANSFER.\n"
    "\n"
    "PROIBICAO ABSOLUTA - SITUACOES INVALIDAS: "
    "CURSANDO, MATRICULADO, EM CURSO, TRANCADO, REPROVADO, CANCELADO, INDEFINIDO e qualquer situacao "
    "NAO listada acima sao TERMINANTEMENTE PROIBIDAS como base para dispensa. "
    "SE uma disciplina do historico tiver situacao CURSANDO (ou variante), ela NUNCA pode ser usada como equivalente, "
    "independentemente de qualquer outro fator. "
    "CARGA HORARIA NAO E VARIAVEL PARA DISPENSA. "
    "Nao importa se a CH e superior, igual ou inferior: se a situacao for CURSANDO, a dispensa e IMPOSSIVEL.\n"
    "\n"
    "CH: porcentagem=(ch_hist_total/ch_nova)*100, 1 decimal. ch_nova<=0->porcentagem=0.\n"
    "OBS: ch>=nova->'CH compativel.'; ch<nova->'CH inferior (historico=XXh < nova=YYh).'\n"
    "IMPORTANTE: carga horaria NAO determina dispensa. Mesmo com CH inferior, a disciplina PODE ser dispensada SE situacao valida. "
    "A CH e apenas informativa para registro, NAO e criterio de aprovacao/rejeicao.\n"
    "\n"
    "NOME_REGISTRO: match exato->nome original; agrupamento->'Base I, II e III'; "
    "generica->nome sem numeral; bases diferentes->'Nome1 & Nome2'. Derivar das selecionadas. Possuir no **máximo 200 caracteres**\n"
    "\n"
    "PERIODO (SEM INFERENCIA): retornar apenas 'ano' e 'semestre' (sem campo periodo).\n"
    "Extrair do campo periodo/ANO_SEM do historico SOMENTE se estiver explicitamente escrito no documento.\n"
    "- Se vier no formato '2020/1', '2020-1', '2020.1' => ano='2020', semestre='1'.\n"
    "- Puxar o que realmente estiver escrito, sem inferir. Ex: '2020' semestre='71' => ano='2020', semestre='71'. "
    "- Se vier como '1o semestre 2020' ou equivalente => semestre='1' e ano='2020'.\n"
    "- Se vier apenas o ANO (ex: '2020') e NAO houver semestre explicito => ano='2020' e semestre=null.\n"
    "- Se o documento for anual e nao trouxer semestre explicito => ano conforme documento e semestre=null.\n"
    "PROIBIDO: inventar, estimar, calcular ou assumir semestre (ex: nunca usar '4' como fallback).\n"
    "\n"
    "CH: OBRIGATORIO extrair carga_horaria de cada disciplina. Se ausente, usar 0.\n"
    "\n"
    "FILTRO FINAL OBRIGATORIO: O JSON de saida deve conter SOMENTE disciplinas que TEM equivalencia valida "
    "e PODEM ser dispensadas (possivel_dispensa=true). "
    "Se uma nova disciplina NAO tem equivalente, NAO inclua no array. "
    "Se disciplinas_cursadas_equivalentes esta vazio, NAO inclua no array. "
    "Se TODOS os equivalentes encontrados tiverem situacao CURSANDO ou outra invalida, "
    "a nova disciplina NAO pode ser dispensada e NAO deve aparecer no array. "
    "O array comparacao_disciplinas so deve ter itens com possivel_dispensa=true E "
    "com pelo menos um equivalente em situacao VALIDA (APROVADO ou DISPENSADO e variantes).\n"
    '{"comparacao_disciplinas":[{"nova_disciplina":{"codigo":"","nome":"","carga_horaria":0},'
    '"disciplinas_cursadas_equivalentes":[{"codigo":"","ano":"","semestre":"",'
    '"nome":"","carga_horaria":0,"creditos":0,"nota":"","situacao":""}],'
    '"porcentagem_aproveitamento":0,"possivel_dispensa":true,"observacao":"","nome_registro":""}]}'
)

PROMPT_EXTRACAO = (
    "Extraia o historico escolar do documento. Retorne JSON.\n"
    "\n"
    "IDIOMA: O documento pode estar em QUALQUER idioma (portugues, ingles, espanhol, etc). "
    "Extraia os dados independente do idioma. Mantenha os nomes das disciplinas no idioma ORIGINAL do documento. "
    "Traduza apenas campos de situacao para o padrao definido abaixo.\n"
    "\n"
    "REGRAS:\n"
    "- Apenas dados presentes, nao invente. Tolere ruidos OCR.\n"
    "- NOME DA DISCIPLINA: usar o nome completo/descritivo, NAO o codigo. "
    "Se so existe codigo sem nome descritivo, usar o codigo como nome.\n"
    "- CARGA HORARIA: OBRIGATORIO extrair de cada disciplina. Inteiro (ex:60,80). Se ausente, usar 0.\n"
    "NOTA (REGRAS DE MEDIA):\n"
    "- A nota e INFORMATIVA e NAO determina dispensa.\n"
    "- Se 'disciplinas_cursadas_equivalentes' tiver APENAS 1 item: manter a nota original desse item.\n"
    "- Se 'disciplinas_cursadas_equivalentes' tiver MAIS DE 1 item (agrupamento):\n"
    "  * Calcular a MEDIA ARITMETICA das notas numericas dos itens.\n"
    "  * Notas podem vir como string com virgula ou ponto (ex: '7,5' ou '7.5'). Converter para numero.\n"
    "  * Ignorar notas vazias, '0.00' quando claramente ausente, ou nao numericas.\n"
    "  * Se nenhuma nota valida existir, retornar nota='' (vazio).\n"
    "  * Formatar a nota media com 2 casas decimais como string (ex: '7.33').\n"
    "- Onde colocar a nota media:\n"
    "  * No caso de agrupamento, no array 'disciplinas_cursadas_equivalentes', preencher o campo 'nota' de TODOS os itens com a MESMA nota media calculada.\n"
    "  * (Opcional se quiser) adicionar na 'observacao' algo como: 'Nota media calculada a partir de X disciplinas'.\n"
    "\n"
    "- Situacao: APROVADO,REPROVADO,CURSANDO,TRANCADO,DISPENSADO,EQUIVALENCIA,CANCELADO,INDEFINIDO "
    "(AP->APROVADO, RP->REPROVADO, PASS/PASSED/CREDIT/TRANSFER->APROVADO etc.)\n"
    "- Incluir APENAS disciplinas com situacao APROVADO ou DISPENSADO (e suas variantes). "
    "PROIBIDO incluir disciplinas com situacao CURSANDO, TRANCADO, REPROVADO, CANCELADO ou INDEFINIDO. "
    "Disciplinas que o aluno ESTA CURSANDO no momento NAO devem aparecer no JSON de saida.\n"
    "- PERIODO: retornar apenas 'ano' e 'semestre' por disciplina (sem campo periodo).\n"
    "  Extrair do campo periodo/ANO_SEM. Ano a esquerda, semestre apos hifen/barra.\n"
    "  Semestral: ano e semestre encontrado. Anual: ano e semestre='4'.\n"
    "  Se so tem ano sem semestre, semestre='4'.\n"
    "- Campo vazio: texto->'', numero->0, opcional->null\n"
    "\n"
    "SCHEMA:\n"
    '{"documento":{"tipo":"HISTORICO_ESCOLAR","instituicao":{"nome":"","campus":"","cidade":"","uf":"","cnpj":null},'
    '"emissao":{"data":"","numero_documento":"","validacao_autenticidade":""}},'
    '"aluno":{"nome":"","matricula":"","cpf":"","rg":"","data_nascimento":""},'
    '"curso":{"nome":"","nivel":"","modalidade":"","turno":"","matriz_curricular":"","periodo_ingresso":"","forma_ingresso":""},'
    '"situacao_academica":{"status":"","periodo_atual":"","data_situacao":""},'
    '"indicadores":{"cr_ira":"","creditos_obtidos":0,"creditos_totais":0,"carga_horaria_cumprida":0,"carga_horaria_total":0,"percentual_integralizacao":""},'
    '"disciplinas":{"NOME_DISCIPLINA":{"ano":"","semestre":"","codigo":"","carga_horaria":0,"creditos":0,"nota":"","frequencia":"","situacao":"","observacoes":""}},'
    '"observacoes_gerais":""}'
)

# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class GeminiHistorico:
    def __init__(self) -> None:
        self.client = genai.Client(api_key=GEMINI_API_KEY_PRIMARY)

    # -- public API ---------------------------------------------------------

    def send_for_docling(
        self,
        docling_doc: Union[Dict[str, Any], List[Any]],
        grade: Union[Dict[str, Any], List[Any]],
    ) -> Any:
        partes: List[str] = [PROMPT_COMPARACAO]

        partes.append("\n\nGRADE (novas disciplinas):\n" + json.dumps(grade, ensure_ascii=False))

        # Lista de extracoes ZIP: cada item tem chaves 'arquivo' e 'conteudo'
        if isinstance(docling_doc, list) and docling_doc and "arquivo" in docling_doc[0]:
            for i, doc in enumerate(docling_doc, 1):
                partes.append(
                    f"\n\nDOC {i} ({doc['arquivo']}):\n"
                    + json.dumps(doc["conteudo"], ensure_ascii=False)
                )
        else:
            partes.append(
                "\n\nHISTORICO EXTRAIDO:\n"
                + json.dumps(docling_doc, ensure_ascii=False)
            )

        response = self.client.models.generate_content(
            model=MODELO,
            contents=["".join(partes)],
            config=GEN_CONFIG,
        )

        return safe_json_load(response.text)

    def ler_documento(self, url: str, tipo: str) -> Dict[str, Any]:
        try:
            doc_data = baixar_arquivo(url)

            response = self.client.models.generate_content(
                model=MODELO,
                contents=[
                    types.Part.from_bytes(data=doc_data, mime_type=tipo),
                    PROMPT_EXTRACAO,
                ],
                config=GEN_CONFIG,
            )

            return safe_json_load(response.text)

        except Exception as e:
            return {"Erro": True, "Motivo": str(e)}

    def transform_to_json(
        self,
        historico: Union[str, Dict[str, Any], List[Any]],
        grade: Union[Dict[str, Any], List[Any]],
    ) -> Dict[str, Any]:
        # Se veio como string JSON, tenta parsear para dict/list
        if isinstance(historico, str):
            try:
                parsed = json.loads(historico)
                if isinstance(parsed, (dict, list)):
                    historico = parsed
            except (json.JSONDecodeError, ValueError):
                pass

        # Historico interno (JSON) - pula extracao, vai direto para comparacao
        if isinstance(historico, (dict, list)):
            comparacao = self.send_for_docling(docling_doc=historico, grade=grade)
            return {"extracao": historico, "comparacao": comparacao}

        # Historico externo (URL de arquivo) - faz extracao + comparacao
        url: str = historico
        ext = "." + url.lower().rsplit(".", 1)[-1]

        if ext in MIME_TYPES:
            extracao = self.ler_documento(url, MIME_TYPES[ext])
            comparacao = self.send_for_docling(docling_doc=extracao, grade=grade)
            return {"extracao": extracao, "comparacao": comparacao}

        if ext == ".zip":
            return self._processar_zip(url, grade)

        return {"Erro": True, "Motivo": "Tipo de arquivo nao suportado"}

    # -- private helpers ----------------------------------------------------

    def _processar_zip(
        self,
        url: str,
        grade: Union[Dict[str, Any], List[Any]],
    ) -> Dict[str, Any]:
        try:
            zip_bytes = baixar_arquivo(url)
            arquivos = self._extrair_arquivos_zip(zip_bytes)

            extracoes: List[Dict[str, Any]] = []
            for arquivo in arquivos:
                mime = MIME_TYPES.get(arquivo.suffix.lower(), "image/jpeg")
                resultado = self.ler_documento(url=str(arquivo), tipo=mime)
                extracoes.append({"arquivo": arquivo.name, "conteudo": resultado})

            comparacao = self.send_for_docling(docling_doc=extracoes, grade=grade)
            return {
                "extracao": {"tipo": "ZIP_MULTIPLOS_DOCUMENTOS", "documentos": extracoes},
                "comparacao": comparacao,
            }
        except Exception as e:
            return {"Erro": True, "Motivo": f"Ao tentar extrair ZIP: {e}"}

    @staticmethod
    def _extrair_arquivos_zip(conteudo_zip: bytes) -> List[Path]:
        # NOTE: The temp directory is intentionally NOT cleaned up here because
        # the returned file paths must remain valid for downstream processing
        # (lerDocumento reads them from disk). The caller is responsible for
        # cleanup, or the OS will reclaim the space on reboot.
        temp_dir = Path(tempfile.mkdtemp())
        zip_path = temp_dir / "arquivo.zip"
        zip_path.write_bytes(conteudo_zip)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        arquivos = sorted(
            [f for f in temp_dir.rglob("*") if f.is_file() and f.suffix.lower() in EXTENSOES_SUPORTADAS],
            key=lambda f: f.name.lower(),
        )

        if not arquivos:
            raise ValueError("ZIP nao contem arquivos suportados")

        return arquivos

    # -- backward-compatible camelCase aliases ------------------------------
    lerDocumento = ler_documento
    transformToJson = transform_to_json


# Backward-compatible alias for the old class name
Gemini = GeminiHistorico
