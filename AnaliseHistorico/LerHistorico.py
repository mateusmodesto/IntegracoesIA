from datetime import datetime
import subprocess
from google import genai
from google.genai import types
import httpx
import requests
import os
import re
import json
import zipfile
import tempfile
from pathlib import Path

class Gemini():
    def __init__(self):
        self.client = genai.Client(api_key="AIzaSyAZ9IWdDOKKzSt8283YbPGF-iPV4esknkA")
        
        self.prompt = """
            Você é um sistema especializado em comparação de disciplinas de históricos escolares brasileiros. Você recebe dados estruturados (JSON) já extraídos.
            Sua tarefa é:
            1) comparar as disciplinas já cursadas/aprovadas com as novas disciplinas;
            2) identificar equivalências principalmente por NOME;
            3) tratar corretamente disciplinas com numeração (I, II, III... / 1, 2, 3...) e fazer agrupamento quando necessário;
            4) retornar SOMENTE as novas disciplinas que forem DISPENSADAS (possivel_dispensa = true) em um JSON final.

            ENTRADAS

            A) JSON DO HISTÓRICO (disciplinas já cursadas – já filtradas para aprovadas/dispensadas, mas valide)
            Formato: um array contendo 1 objeto com várias chaves (cada chave é uma disciplina):
            [
            {
                "disciplina1": {
                "periodo": "2022/1",
                "codigo": "EXT101",
                "nome": "Práticas Extensionistas I",
                "carga_horaria": 60,
                "creditos": 2,
                "nota": "8.00",
                "situacao": "AP"
                }
            }
            ]

            B) JSON DE NOVAS DISCIPLINAS (disciplinas que o aluno irá cursar)
            Formato: um array contendo 1 objeto com várias chaves (cada chave é uma disciplina):
            [
            {
                "disciplina1": { "codigo": "EXT200", "nome": "Práticas Extensionistas", "carga_horaria": 120 }
            }
            ]

            OBJETIVO
            Retornar um JSON com comparacao_disciplinas contendo APENAS as novas disciplinas que podem ser dispensadas por equivalência com o histórico, aplicando as regras de numeração abaixo.

            NORMALIZAÇÃO (RÁPIDA E ROBUSTA)
            Antes de comparar nomes (sem explicar no output):
            - transformar em minúsculas
            - remover acentos
            - remover pontuação e símbolos
            - reduzir espaços múltiplos

            DETECÇÃO DE NUMERAÇÃO (SUFIXO FINAL)
            Uma disciplina pode ter SUFIXO NUMÉRICO FINAL, por exemplo:
            - "Direito Penal I", "Direito Penal II", "Direito Penal IV"
            - "Estágio Supervisionado 1", "Estágio Supervisionado 2"
            Regras:
            - Considere como sufixo final válido:
            a) numerais romanos: I, II, III, IV, V, VI, VII, VIII, IX, X
            b) números arábicos: 1, 2, 3, 4, 5...
            - Extraia:
            - base_name: nome sem o sufixo numérico final (após normalização)
            - numeral: o sufixo (se existir); caso contrário numeral = "" (vazio)

            Exemplos:
            - "Direito Penal I" -> base_name="direito penal", numeral="I"
            - "Direito Penal" -> base_name="direito penal", numeral=""
            - "Estagio Supervisionado 2" -> base_name="estagio supervisionado", numeral="2"

            IMPORTANTE:
            - Remova SOMENTE numeração no FINAL do nome.
            - NÃO remova palavras como "modulo", "parte", "nivel", "turma".

            PADRONIZAÇÃO DA SITUAÇÃO (VALIDAÇÃO)
            Padronize situacao do histórico:
            - APROVADO se situacao ∈ ["AP","APR","APROVADO","APROVADA","APROV","Aprovado","Aprovada","DEFERIDO","DEFERIDA","APTO","APTA","AF"]
            - DISPENSADO/EQUIVALENCIA se situacao ∈ ["DISPENSADO","DISPENSA","EQUIVALENCIA","EQUIVALÊNCIA","APROVEITAMENTO","DP"]
            - REPROVADO se situacao ∈ ["RP","REPROVADO","REPROVADA","REPROV."]
            - Caso contrário: "INDEFINIDO"
            A nota pode aparecer como: ["Média", "Média Final", "MF", "Nota"] e deve ser mantida como string.

            COMO ENCONTRAR EQUIVALÊNCIA (FOCO EM VELOCIDADE) 
            1) Match principal por NOME (obrigatório): 
            - Compare o nome normalizado da nova disciplina com o nome normalizado das disciplinas do histórico. 
            - Considere equivalente quando: 
            a) forem iguais (match exato), OU 
            b) um nome contiver o outro (containment) com comprimento mínimo relevante (>= 6 caracteres), OU 
            c) similaridade alta por tokens: 
            - quebre em tokens (palavras) - calcule interseção / tokens_nova 
            - se >= 0.75, considere equivalente

            REGRAS DE NUMERAÇÃO E AGRUPAMENTO (ESSENCIAIS)

            Para cada NOVA disciplina N:

            1) Separe o histórico em grupos por base_name.
            Para o base_name de N, obtenha:
            - H_sem_numeral: disciplinas do histórico com numeral=""
            - H_com_numeral: disciplinas do histórico com numeral != ""

            2) CASO A: NOVA tem NUMERAL (ex.: "Direito Penal I")
            Aplique nesta ordem:
            A1) Se existir no histórico disciplina com MESMO base_name e MESMO numeral:
                - equivalente = essa disciplina (ou disciplinas, se duplicadas)
                - não agrupar com outros numerais
            A2) Se NÃO existir o mesmo numeral, mas existir pelo menos 1 disciplina no histórico SEM numeral (H_sem_numeral não vazio):
                - equivalente = a(s) disciplina(s) sem numeral (serve como “genérica” para qualquer numeração da nova grade)
            A3) Se existir no histórico disciplinas com o mesmo base_name mas com OUTROS numerais (ex.: histórico tem I, II, III e nova é IV):
                - equivalente = AGRUPAR TODAS as disciplinas do histórico disponíveis daquele base_name (I, II, III...) e usar como base para dispensa da nova IV
                - observação deve indicar que a nova é numeral superior e o histórico cobre parcialmente (ex.: "Nova=IV; histórico cobre até III.")
            A4) Se nada disso existir: não dispensa (não entra no output)

            3) CASO B: NOVA NÃO tem NUMERAL (ex.: "Direito Penal")
            B1) Se no histórico existir apenas 1 disciplina daquele base_name (somando com e sem numeral):
                - equivalente = essa disciplina única (sem agrupar mais nada)
            B2) Se no histórico existirem MÚLTIPLAS disciplinas daquele base_name com numerais diferentes (ex.: I, II, III):
                - equivalente = AGRUPAR TODAS (I, II, III...) e retornar como lista (disciplinas_cursadas_equivalentes)
                - observação deve indicar agrupamento por múltiplas variantes
            B3) Se no histórico existirem tanto uma genérica (sem numeral) quanto numeradas:
                - equivalente = use PRIMEIRO a genérica (sem numeral) se ela estiver APROVADA/DISPENSADA/EQUIVALENCIA;
                - caso a genérica não seja válida, use as numeradas válidas e agrupe.

            VALIDAÇÃO POR SITUAÇÃO (SÓ CONSIDERAR VÁLIDAS)
            Ao selecionar equivalentes (simples ou agrupados), inclua SOMENTE disciplinas do histórico cuja situação padronizada seja:
            "APROVADO" ou "DISPENSADO" ou "EQUIVALENCIA"
            Se o conjunto final ficar vazio: não dispensa (não entra no output).

            CARGA HORÁRIA E PORCENTAGEM
            - Se equivalência for 1 disciplina:
            ch_historico_total = carga_horaria dessa disciplina
            - Se equivalência for agrupada:
            ch_historico_total = soma(carga_horaria) das disciplinas equivalentes selecionadas

            porcentagem_aproveitamento = (ch_historico_total / ch_nova) * 100
            - arredonde para 1 casa decimal
            - Se ch_nova <= 0:
            porcentagem_aproveitamento = 0
            observacao = "CH da nova disciplina ausente/zero; dispensa baseada em equivalência por nome e situação."

            CRITÉRIO DE DISPENSA
            Defina possivel_dispensa = true quando:
            - existir equivalência (simples ou agrupada) após validação de situação

            Observação obrigatória sobre carga horária:
            - Se ch_historico_total >= ch_nova: "Equivalente por nome; CH compatível."
            - Se ch_historico_total < ch_nova: "Equivalente por nome; CH inferior (historico=XXh < nova=YYh)."
            - Se A3 ocorreu (nova numeral maior do que o máximo do histórico): inclua também:
            "Nova=NUM; histórico cobre até NUM_MAX."

            REGRA PARA PREENCHIMENTO DO CAMPO "nome_registro"
            Em cada item retornado em "comparacao_disciplinas", preencha "nome_registro" seguindo estas regras:

            1) Definição do "nome_registro"
            - "nome_registro" deve representar, de forma resumida e informativa, o(s) nome(s) das disciplina(s) do histórico efetivamente utilizadas como equivalência.

            2) Caso a NOVA disciplina contenha numeração (tem numeral) e a comparação NÃO foi feita por numeração (ou seja, não houve match exato do MESMO numeral; ocorreu uso de genérica sem numeral ou agrupamento por outros numerais):
            - "nome_registro" deve agrupar as numerações efetivamente utilizadas do histórico.
            - Formato sugerido:
            "<base_name com ortografia corrigida> <lista_de_numerais_utilizados>"
            Ex.: "Direito Penal I, II e III"
            - Regras de formatação:
            - Se houver 1 numeral: "I"
            - Se houver 2 numerais: "I e II"
            - Se houver 3+ numerais: "I, II e III" (usar vírgulas e "e" antes do último)
            - Se houver mistura de romanos e arábicos, preserve como aparece nos nomes originais (preferir romanos se a maioria estiver em romanos).
            - Se as disciplinas usadas incluírem uma versão sem numeral (genérica), use apenas o nome sem numeral (ex.: "Direito Penal") e NÃO liste numerais.

            3) Caso contrário (comparação feita por numeração ou não houve agrupamento):
            - "nome_registro" deve ser apenas o nome da disciplina utilizada (do histórico) com ortografia corrigida.
            Ex.: se foi match exato "Direito Penal II" -> nome_registro = "Direito Penal II"
            Ex.: se usou a genérica "Direito Penal" -> nome_registro = "Direito Penal"

            4) Caso as disciplinas utilizadas tenham NOMES DIFERENTES (não compartilham exatamente o mesmo base_name após normalização), mesmo que tenham sido agrupadas:
            - "nome_registro" deve concatenar os nomes distintos usando o separador:
            " Nome 1 " & " Nome 2 "
            - Se forem 3 ou mais nomes diferentes:
                "Nome 1" & "Nome 2" & "Nome 3"
            - Em todos os casos, use os nomes com ortografia corrigida.
            - Se algum desses nomes diferentes também tiver numeração a ser agrupada (regra 2), aplique a regra 2 dentro de cada bloco antes de concatenar.
                Ex.: "Práticas Extensionistas I, II e III" & "Atividades Extensionistas"

            5) Origem do "nome_registro"
            - Sempre derive o "nome_registro" a partir das disciplinas em "disciplinas_cursadas_equivalentes" que realmente foram selecionadas (após validação de situação).
            - Nunca invente numerais ou nomes que não estejam presentes nas disciplinas selecionadas.

            6) Origem do "ano" e "semestre"
            - Sempre extrair as informações do "periodo", nele sempre estará as informações de ano e semestre
            - As informações estarão:
                Ex: (ano)-(semestre)
                OU  (ano)(letra)-(semestre)
                OU  (ano)/(semestre)
                OU  (ano)(letra)-(semestre)
                
            - O ano sempre vem na esquerda e o semestre após o hifen.

            SAÍDA (OBRIGATÓRIA)
            Retorne EXCLUSIVAMENTE um JSON válido, sem texto fora do JSON.
            IMPORTANTE: incluir APENAS itens com possivel_dispensa = true.

            ESTRUTURA (SEMPRE LISTA NO HISTÓRICO)
            Use sempre "disciplinas_cursadas_equivalentes" como LISTA (mesmo que tenha 1 item).

            {
            "comparacao_disciplinas": [
                {
                "nova_disciplina": {
                    "codigo": "",
                    "nome": "",
                    "carga_horaria": 0
                },
                "disciplinas_cursadas_equivalentes": [
                    {
                    "codigo": "",
                    "periodo": "",
                    "ano": "",
                    "semestre": "",
                    "nome": "",
                    "carga_horaria": 0,
                    "creditos": 0,
                    "nota": "",
                    "situacao": ""
                    }
                ],
                "porcentagem_aproveitamento": 0,
                "possivel_dispensa": true,
                "observacao": "",
                "nome_registro": ""
                }
            ]
            }

            ORIENTAÇÕES FINAIS (DESEMPENHO)
            - Não explique etapas, não use markdown, não inclua texto fora do JSON.
            - Eficiência:
            1) crie índices do histórico por base_name e por numeral
            2) para cada nova disciplina, aplique as regras CASO A/B na ordem definida
            - Retorne apenas disciplinas dispensadas no JSON final, com ortografia corrigida no campo "nome".


            """
  
    def send_for_docling(self, docling_doc=None, historico_interno=None, grade=None):

        conteudo = (
            self.prompt
            + "\n\nJSON DE DISCIPLINAS NOVAS (GRADE):\n"
            + json.dumps(grade, ensure_ascii=False, indent=2)
        )

        if historico_interno:
            conteudo += (
                "\n\nHISTÓRICO INTERNO (BASE PRIMÁRIA — PRIORIDADE MÁXIMA):\n"
                "Use este histórico como referência principal. "
                "Ele pode estar incompleto.\n"
                + json.dumps(historico_interno, ensure_ascii=False, indent=2)
            )

        if isinstance(docling_doc, list):
            conteudo += (
                "\n\nDOCUMENTOS EXTERNOS (COMPLEMENTARES AO HISTÓRICO):\n"
                "Estes documentos podem conter disciplinas adicionais "
                "ou informações ausentes no histórico interno.\n"
            )
            for i, doc in enumerate(docling_doc, 1):
                conteudo += (
                    f"\n--- DOCUMENTO {i}: {doc['arquivo']} ---\n"
                    + json.dumps(doc['conteudo'], ensure_ascii=False, indent=2)
                )

        elif docling_doc:
            conteudo += (
                "\n\nDOCUMENTO EXTERNO (COMPLEMENTAR AO HISTÓRICO):\n"
                + json.dumps(docling_doc, ensure_ascii=False, indent=2)
            )

        response = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[conteudo]
        )

        return self._safe_json_load(response.text)
    
    def lerDocumento(self, url, tipo):
        promptJson = '''
            Você é um sistema especializado em leitura (OCR), interpretação e estruturação de históricos escolares de instituições de ensino superior brasileiras. Você receberá um documento em PDF ou imagem (escaneado ou digital). Sua tarefa é extrair as informações relevantes do histórico e retornar EXCLUSIVAMENTE um JSON válido no esquema definido abaixo.

            ENTRADA
            - Um histórico escolar (PDF ou imagem).
            - O documento pode conter ruídos de digitalização, carimbos, assinaturas, tabelas, abreviações, variações de layout e múltiplas páginas.
            - Caso você identifique que o documento é uma grade escolar ou um programa de disciplinas, pode retornar um array vazio.

            OBJETIVO
            1) Ler o documento (aplicar OCR quando necessário).
            2) Identificar e extrair todos os dados acadêmicos essenciais:
            - Dados do aluno
            - Dados do curso e instituição
            - Dados de matrícula/ingresso
            - Todas as disciplinas listadas no histórico (cursadas/dispensadas/equivalência/reprovadas/cursando)
            - Totais e indicadores (quando existirem no documento), como carga horária total, créditos totais, CR/IRA, situação acadêmica, data de emissão.
            3) Estruturar a saída no JSON abaixo, mantendo consistência de tipos e preenchendo valores ausentes com "" ou 0 ou null conforme indicado.

            REGRAS IMPORTANTES
            - NÃO invente informações. Extraia apenas o que estiver no documento.
            - Seja tolerante a variações e erros de OCR (acentos, letras trocadas, separadores).
            - Ao detectar valores numéricos:
            - Carga horária/Créditos: use número inteiro (ex.: 60).
            - Notas: mantenha como string exatamente como aparece (ex.: "8,5", "7.0", "MB", "A", "AP").
            - Padronize a “situação” da disciplina quando possível para um destes valores:
            "APROVADO", "REPROVADO", "CURSANDO", "TRANCADO", "DISPENSADO", "EQUIVALENCIA", "CANCELADO", "INDEFINIDO"
            - Se o documento usar siglas (AP, RP etc.), converta para a forma padronizada.
            - Se não der para inferir, use "INDEFINIDO".
            - Se um campo não for encontrado:
            - Textos: "" (string vazia)
            - Números inteiros: 0
            - Campos opcionais gerais (ex.: CNPJ, campus): null quando fizer sentido
            - Não inclua explicações, comentários ou markdown fora do JSON.
            - Mantenha a ordem das disciplinas conforme o histórico (por período/semestre) se essa ordem existir.
            - A nota de sair no padrão: 0.00 (necessáriamente)

            DICAS DE EXTRAÇÃO (SEM SAÍDA DE TEXTO)
            - Procure por cabeçalhos como: “Aluno”, “Matrícula/RA”, “Curso”, “Período de ingresso”, “Histórico Escolar”, “Componentes Curriculares”, “Disciplinas”.
            - A tabela de disciplinas normalmente contém colunas como: período/semestre, código, disciplina, CH, créditos, nota/média, situação.
            - Se existirem totais (CR/IRA, CH total, créditos totais, integralização), capture nos campos correspondentes.

            FORMATO DE SAÍDA (OBRIGATÓRIO)
            Retorne EXCLUSIVAMENTE este JSON (sem nenhum texto antes/depois):

            {
            "documento": {
                "tipo": "HISTORICO_ESCOLAR",
                "instituicao": {
                "nome": "",
                "campus": "",
                "cidade": "",
                "uf": "",
                "cnpj": null
                },
                "emissao": {
                "data": "",
                "numero_documento": "",
                "validacao_autenticidade": ""
                }
            },
            "aluno": {
                "nome": "",
                "matricula": "",
                "cpf": "",
                "rg": "",
                "data_nascimento": ""
            },
            "curso": {
                "nome": "",
                "nivel": "",
                "modalidade": "",
                "turno": "",
                "matriz_curricular": "",
                "periodo_ingresso": "",
                "forma_ingresso": ""
            },
            "situacao_academica": {
                "status": "",
                "periodo_atual": "",
                "data_situacao": ""
            },
            "indicadores": {
                "cr_ira": "",
                "creditos_obtidos": 0,
                "creditos_totais": 0,
                "carga_horaria_cumprida": 0,
                "carga_horaria_total": 0,
                "percentual_integralizacao": ""
            },
            "disciplinas": {
                "nome_disciplina": {
                    "periodo": "",
                    "codigo": "",
                    "carga_horaria": 0,
                    "creditos": 0,
                    "nota": "",
                    "frequencia": "",
                    "situacao": "",
                    "observacoes": ""
                }
            },
            "observacoes_gerais": ""
            }

            VALIDAÇÕES FINAIS (ANTES DE RESPONDER)
            - O JSON deve ser válido (aspas, vírgulas, colchetes).
            - “disciplinas” deve conter TODAS as disciplinas encontradas no histórico (apenas aprovadas e dispensadas).
            - Se o documento tiver mais de uma página, combine as informações corretamente (evite duplicar linhas iguais).
            - Não retorne texto fora do JSON.

        '''
        try:
            if url.startswith("http"):
                doc_data = httpx.get(url, timeout=60).content
            else:
                with open(url, "rb") as f:
                    doc_data = f.read()

            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    types.Part.from_bytes(
                        data=doc_data,
                        mime_type=tipo,
                    ),
                    promptJson
                ]
            )

            return self._safe_json_load(response.text)

        except Exception as e:
            return {"Erro": True, "Motivo": str(e)}
        
    def transformToJson(self, url, historico_interno: None, grade):
        ext = url.lower().split(".")[-1]
        if ext in ["jpg", "jpeg", "png", "tiff"]:
            extracao = self.lerDocumento(url, 'image/jpeg')
            return {"extracao": extracao, "historico_interno": historico_interno, "comparacao": self.send_for_docling(docling_doc=extracao, historico_interno=historico_interno, grade=grade)}
        elif ext == "pdf":
            extracao = self.lerDocumento(url, 'application/pdf')
            return {"extracao": extracao, "historico_interno": historico_interno, "comparacao": self.send_for_docling(docling_doc=extracao, historico_interno=historico_interno, grade=grade)}
        elif ext == "zip":
            try:
                zip_bytes = httpx.get(url, timeout=60).content
                arquivos = self.extrair_arquivos_zip(zip_bytes)

                extracoes = []

                for arquivo in arquivos:
                    mime = (
                        "application/pdf"
                        if arquivo.suffix.lower() == ".pdf"
                        else "image/jpeg"
                    )

                    resultado = self.lerDocumento(
                        url=str(arquivo),
                        tipo=mime
                    )

                    extracoes.append({
                        "arquivo": arquivo.name,
                        "conteudo": resultado
                    })

                return {
                    "extracao": {
                        "tipo": "ZIP_MULTIPLOS_DOCUMENTOS",
                        "documentos": extracoes
                    },
                    "historico_interno": historico_interno,
                    "comparacao": self.send_for_docling(
                        docling_doc=extracoes,
                        historico_interno=historico_interno,
                        grade=grade
                    )
                }

            except Exception as e:
                return {"Erro": True, "Motivo": f"Ao tentar extrair ZIP {str(e)}"}


            
        else:
            return {"Erro": True, "Motivo": "Tipo de arquivo não suportado"}
        
   

    def extrair_arquivos_zip(self, conteudo_zip: bytes):
        temp_dir = Path(tempfile.mkdtemp())

        zip_path = temp_dir / "arquivo.zip"
        zip_path.write_bytes(conteudo_zip)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        arquivos = []

        for arquivo in temp_dir.rglob("*"):
            if arquivo.is_file() and arquivo.suffix.lower() in [
                ".pdf", ".jpg", ".jpeg", ".png", ".tiff"
            ]:
                arquivos.append(arquivo)

        if not arquivos:
            raise ValueError("ZIP não contém arquivos suportados")

        # ordena para manter previsibilidade (ex: nome ou tamanho)
        arquivos.sort(key=lambda f: f.name.lower())

        return arquivos



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

