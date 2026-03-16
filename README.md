# FlaskPyIA - Sistema de Processamento de Documentos com IA

API Flask para processamento inteligente de documentos educacionais usando Google Gemini.
Atende a instituicao Escolas Padre Anchieta, integrando com o sistema academico Lyceum.

---

## Estrutura do Projeto

```
FlaskPyIA/
├── .env                            # Variaveis de ambiente (NAO commitar)
├── .gitignore
├── API.py                          # Servidor Flask principal
├── API_FAST.py                     # Versao FastAPI (alternativa, nao ativa)
├── requirements.txt
├── __init__.py
│
├── shared/                         # Codigo compartilhado entre modulos
│   ├── config.py                   # Carrega .env, exporta DATABASE_CONFIG, API keys, logging
│   ├── database.py                 # BaseDatabaseManager (conexao + queries base)
│   ├── gemini_helpers.py           # safe_json_load(), baixar_arquivo()
│   └── utils.py                    # Utils: CPF, datas, formatacao, estados
│
├── LeituraDocumentos/              # Validacao de documentos de alunos
│   ├── simple_main_flask.py        # Orquestrador principal
│   ├── LerDocumentoClass.py        # Integra Gemini (validacao + extracao)
│   ├── database_manager.py         # Herda BaseDatabaseManager + metodos do dominio
│   ├── api_client.py               # Cliente HTTP + ViaCEP
│   └── migration_classes.py        # Migracao por tipo de documento
│
├── PROUNI/                         # Documentos do programa PROUNI
│   ├── simple_main_flask.py        # Orquestrador PROUNI
│   ├── LerDocumentoClass.py        # Prompts Gemini especificos PROUNI
│   ├── database_manager.py         # Herda BaseDatabaseManager + metodos PROUNI
│   ├── simple_main_manual.py       # Processamento manual/batch
│   └── DocumentosPendentes.sql     # Query auxiliar
│
├── AnaliseHistorico/               # Analise de historico escolar
│   ├── simple_main.py              # Orquestrador (roda em background)
│   ├── LerHistorico.py             # Gemini: extracao + comparacao de grades
│   └── database_manager.py         # Herda BaseDatabaseManager + metodos de dispensa
│
├── GerarPeticao/                   # Geracao de documentos juridicos
│   ├── agente_rag.py               # Gera .docx a partir de templates do banco
│   ├── database_manager.py         # Herda BaseDatabaseManager + templates
│   └── front/                      # Frontend PHP do modulo juridico
│
└── ComparadorTabela/               # Comparador de planilhas de compras
    └── processamento.py            # (modulo externo, importado em API.py)
```

---

## Configuracao

Todas as credenciais ficam no arquivo `.env` na raiz do projeto:

```env
GEMINI_API_KEY_PRIMARY=...
GEMINI_API_KEY_PROUNI=...
DB_HOST=192.168.0.9
DB_PORT=1433
DB_NAME=dtb_lyceum_prod
DB_USER=lyceum
DB_PASSWORD=lyceum
AWS_API_KEY=...
FLASK_PORT= ...
```

O modulo `shared/config.py` carrega essas variaveis via `python-dotenv` e exporta constantes usadas por todos os modulos.

---

## Endpoints da API

Servidor: `0.0.0.0:5010`

### POST `/validar`
Valida documentos de alunos (RG, CPF, CNH, certidoes, comprovantes, etc).

**Payload:**
```json
{
  "arquivo": "id_do_arquivo",
  "aluno": "id_do_aluno",
  "posicao": "posicao_documento",
  "usuario": "id_usuario",
  "curso_entrega": "id_curso"
}
```

**Fluxo interno:**
1. Busca o documento no banco (base64/URL)
2. Gemini `flash-lite` valida se e documento e identifica o tipo
3. Gemini `flash` extrai campos (nome, numero, datas, etc)
4. `migration_classes.py` grava os dados extraidos nas tabelas do Lyceum

**Tipos de documento suportados:**
RG, CPF, CNH, Certidao de Nascimento/Casamento, Comprovante de Residencia,
Historico Escolar, Carteira de Vacinacao, Certificado de Reservista,
Titulo de Eleitor, Declaracao de Transferencia, Diploma de Graduacao

---

### POST `/PROUNI`
Valida documentos especificos do programa PROUNI.

**Payload:**
```json
{
  "arquivo": "id_do_arquivo",
  "pessoa": "id_da_pessoa",
  "tipo_documento": "tipo"
}
```

**Documentos PROUNI suportados:**
CPF, RG, Historico Escolar, Declaracao de Auxilio, CTPS,
Declaracao de Renda, Pro-Labore, entre outros.

Possui regras de substituicao (ex: CNH substitui RG e CPF).

---

### POST `/analiseHistorico`
Analisa historico escolar para dispensa de disciplinas. Processamento assincrono.

**Payload:**
```json
{
  "aluno": "id_aluno",
  "historico": "dados_historico",
  "grade": "grade_curricular",
  "candidato": "id_candidato",
  "id_analise": "id",
  "usuario_id": "id_usuario",
  "tipo_historico": "tipo"
}
```

**Fluxo:**
1. Retorna `200` imediatamente com `"status": "aceito"`
2. Processa em thread background
3. Gemini extrai disciplinas do historico
4. Compara com grade curricular (nome, carga horaria, ementa)
5. Grava resultado na tabela `ANC_VALIDA_DISPENSA`

Suporta historicos em portugues, ingles e espanhol.

---

### POST `/documentos/gerar`
Gera documento juridico (.docx) a partir de template.

**Payload:**
```json
{
  "tipo_documento": "tipo",
  "secoes": [{"subcategoria": "texto", "ordem": 1}],
  "dados": {"variavel": "valor"}
}
```

Retorna o arquivo `.docx` direto para download.

---

### POST `/sistema_compras/comparar`
Compara planilhas de ordem de compra. Recebe `multipart/form-data`.

**Campos:**
- `conta_certa` - Arquivo base (xlsx)
- `conta_comparar` - Um ou mais arquivos para comparar
- `tolerancia` - Margem de tolerancia (default: 1.0)

### GET `/sistema_compras/download`
Baixa o resultado da ultima comparacao em `.xlsx`.

---

## Respostas Padronizadas

```json
// Sucesso
{"status": "processado", "resultado": {...}}

// Falha no processamento (nao e erro HTTP)
{"status": "nao processado", "resultado": {...}, "payload": {...}}

// Erro de validacao (400)
{"status": "erro", "msg": "Campo 'X' e obrigatorio"}

// Erro interno (500)
{"status": "erro", "msg": "Erro interno", "detail": "..."}
```

---

## Stack Tecnica

| Componente       | Tecnologia                          |
|------------------|-------------------------------------|
| Framework        | Flask + flask-cors                  |
| IA               | Google Gemini (`flash-lite`, `flash`) via `google.genai` |
| Banco de dados   | SQL Server via `pyodbc`             |
| Docs .docx       | `python-docx`                       |
| Planilhas        | `openpyxl` + `pandas`               |
| HTTP Client      | `requests` + `httpx`                |
| CEP              | ViaCEP API                          |
| Config           | `python-dotenv` + `shared/config.py`|
| Logging          | `logging` via `shared.config.get_logger()` |

---

## Banco de Dados

**Servidor:** SQL Server (porta 1433)
**Database:** `dtb_lyceum_prod`

### Tabelas principais

| Tabela | Uso |
|--------|-----|
| `LY_ALUNO` | Dados do aluno |
| `LY_PESSOA` | Dados pessoais |
| `LY_CANDIDATO` | Dados de candidatos |
| `ANCHI_DOCUMENTOS_ENTREGUES` | Documentos submetidos |
| `ANCHI_DOCUMENTOS_ENTREGUES_VALIDA` | Resultado da validacao IA |
| `ANC_VALIDA_DISPENSA` | Resultado da analise de historico |
| `ANC_SIS_JUD_DOC_MODELO` | Templates de documentos juridicos |
| `HD_MUNICIPIO` | Municipios (lookup) |
| `LY_INSTITUICAO` | Instituicoes de ensino |

---

## Como Rodar

```bash
pip install -r requirements.txt
python API.py
```

O servidor sobe em `http://0.0.0.0:5010` com `debug=False`.

---

## Arquitetura Compartilhada (`shared/`)

O modulo `shared/` centraliza codigo que era duplicado entre os modulos:

- **`config.py`** - Carrega `.env`, exporta `DATABASE_CONFIG`, API keys, `get_logger()`
- **`database.py`** - `BaseDatabaseManager` com metodos base (connect, execute_query, fetch_one, fetch_all). Cada modulo herda e adiciona metodos especificos do dominio.
- **`gemini_helpers.py`** - `safe_json_load()` (parse JSON do Gemini) e `baixar_arquivo()` (download por URL)
- **`utils.py`** - Classe `Utils` com formatacao de CPF, datas, CEP, estados, validacao, etc.

---

## Fluxo Geral de Processamento de Documentos

```
Frontend/Integrador
        |
        v
   API.py (Flask)
   valida payload, roteia para modulo
        |
        v
  simple_main_flask.py
  orquestra: busca doc no banco -> chama IA -> salva resultado
        |
        v
  LerDocumentoClass.py
  2 chamadas ao Gemini:
    1. flash-lite -> valida documento (e documento? qual tipo?)
    2. flash -> extrai campos estruturados (JSON)
        |
        v
  migration_classes.py / database_manager.py
  mapeia campos extraidos -> UPDATE nas tabelas do Lyceum
```

---

## Notas para Manutencao

- **Modulos sao independentes:** cada pasta (LeituraDocumentos, PROUNI, etc) tem seu proprio `database_manager`, `LerDocumentoClass` e `simple_main`. Mudancas em um modulo nao afetam os outros.

- **Codigo compartilhado fica em `shared/`:** nao duplique utils, database base ou helpers do Gemini. Importe de `shared`.

- **Credenciais ficam no `.env`:** nunca hardcode API keys ou senhas no codigo. Use `shared.config`.

- **Logging:** use `from shared.config import get_logger` e `logger = get_logger(__name__)` em vez de `print()`.

- **Prompts do Gemini** ficam dentro de cada `LerDocumentoClass.py`. Para ajustar a extracao de um tipo de documento, edite o prompt correspondente.

- **Adicionar novo tipo de documento (LeituraDocumentos):**
  1. Adicionar prompt de extracao em `LerDocumentoClass.py`
  2. Criar classe de migracao em `migration_classes.py`
  3. Registrar no mapeamento de `simple_main_flask.py`

- **Adicionar novo database_manager:** herde de `shared.database.BaseDatabaseManager` e implemente apenas os metodos especificos do dominio.

- **AnaliseHistorico roda em background** via `threading.Thread`. O endpoint retorna imediato, o resultado vai para `ANC_VALIDA_DISPENSA`.

- **GerarPeticao** baixa templates .docx do banco, substitui variaveis `${...}` e retorna o arquivo gerado. Os templates ficam na tabela `ANC_SIS_JUD_DOC_MODELO`.

- **ComparadorTabela** e um modulo para comparar planilhas de ordens de compra. Importado em `API.py` via `from ComparadorTabela.processamento import processar`.

- **API_FAST.py** e uma versao FastAPI dos mesmos endpoints, existe como alternativa mas nao esta ativa em producao.
