from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import uvicorn

# Aplicação FastAPI principal
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


def err(msg, code=400, extra=None):
    """
    Retorna um JSON de erro padronizado.

    - msg: mensagem principal de erro
    - code: HTTP status code
    - extra: informações adicionais (seguras para JSON)
    """

    payload = {
        "status": "erro",
        "msg": msg
    }

    # Garante que tudo em 'extra' seja serializável em JSON
    # Evita erro 500 causado por Exception, objetos, etc.
    if extra:
        safe_extra = {}
        for k, v in extra.items():
            if isinstance(v, (dict, list, str, int, float, bool)) or v is None:
                safe_extra[k] = v
            else:
                safe_extra[k] = str(v)  # conversão defensiva
        payload.update(safe_extra)

    return JSONResponse(content=payload, status_code=code)



@app.post("/validar")
async def validar(request: Request):
    """
    Endpoint responsável por validar documentos enviados.

    Fluxo:
    1. Valida payload básico
    2. Chama o módulo de leitura/validação
    3. Retorna sucesso ou erro sem quebrar o integrador
    """

    import LeituraDocumentos.simple_main_flask as sp

    try:
        # Lê o JSON do body
        try:
            data = await request.json()
        except Exception:
            data = None

        if not isinstance(data, dict):
            return err("JSON inválido ou ausente", 400)

        # Payload normalizado para o módulo de validação
        payload = {
            "arquivo": data.get("arquivo"),
            "aluno": data.get("aluno"),
            "posicao": data.get("posicao"),
            "usuario": data.get("usuario"),
            "curso_entrega": data.get("curso_entrega")
        }

        # Validações obrigatórias (erro do cliente → 400)
        if not payload['arquivo']:
            return err("Campo 'arquivo' é obrigatório", 400)
        if not payload['aluno']:
            return err("Campo 'aluno' é obrigatório", 400)
        if payload['posicao'] is None:
            return err("Campo 'posicao' é obrigatório", 400)

        # Execução principal
        result = sp.main(payload)

        # Retorno padronizado para o integrador
        if result['status'] == 'sucesso':
            return JSONResponse(content={
                "status": "processado",
                "resultado": result
            }, status_code=200)

        elif result['status'] == 'error':
            return JSONResponse(content={
                "status": "nao processado",
                "resultado": result,
                "payload": payload
            }, status_code=200)

        # Caso inesperado, mas sem quebrar o fluxo
        return err("Erro ao processar documento", 200, {"detail": result})

    except Exception as e:
        # Aqui sim erro interno real (500)
        return err("Erro interno", 500, {"detail": str(e)})

@app.post("/PROUNI")
async def prouni(request: Request):
    """
    Endpoint responsável por validar documentos enviados pelo PROUNI.

    Fluxo:
    1. Valida payload básico
    2. Chama o módulo de leitura/validação
    3. Retorna sucesso ou erro sem quebrar o integrador
    """

    import PROUNI.simple_main_flask as sp

    try:
        # Lê o JSON do body
        try:
            data = await request.json()
        except Exception:
            data = None

        if not isinstance(data, dict):
            return err("JSON inválido ou ausente", 400)

        # Payload normalizado para o módulo de validação
        payload = {
            "arquivo": data.get("arquivo"),
            "aluno": data.get("aluno"),
            "tipo_documento": data.get("tipo_documento")
        }

        # Validações obrigatórias (erro do cliente → 400)
        if not payload['arquivo']:
            return err("Campo 'arquivo' é obrigatório", 400)
        if not payload['aluno']:
            return err("Campo 'aluno' é obrigatório", 400)
        if payload['tipo_documento'] is None:
            return err("Campo 'tipo_documento' é obrigatório", 400)

        # Execução principal
        result = sp.main(payload)

        # Retorno padronizado para o integrador
        if result['status'] == 'sucesso':
            return JSONResponse(content={
                "status": "processado",
                "resultado": result
            }, status_code=200)

        elif result['status'] == 'error':
            return JSONResponse(content={
                "status": "nao processado",
                "resultado": result,
                "payload": payload
            }, status_code=200)

        # Caso inesperado, mas sem quebrar o fluxo
        return err("Erro ao processar documento", 200, {"detail": result})

    except Exception as e:
        # Aqui sim erro interno real (500)
        return err("Erro interno", 500, {"detail": str(e)})

@app.post("/analiseHistorico")
async def analiseHistorico(request: Request):
    """
    Endpoint responsável por analisar histórico escolar.

    Aceita:
    - histórico externo (PDF, imagem, ZIP, etc)
    - histórico interno (JSON estruturado)

    O retorno HTTP NÃO indica sucesso da análise,
    apenas sucesso da execução do serviço.
    """

    from AnaliseHistorico import simple_main as ah

    try:
        try:
            data = await request.json()
        except Exception:
            data = None

        if not isinstance(data, dict):
            return err("JSON inválido ou ausente", 400)

        # Histórico interno pode vir como string JSON
        historico_interno = data.get("historico_interno")
        if historico_interno:
            try:
                historico_interno = json.loads(historico_interno)
            except json.JSONDecodeError:
                return err("historico_interno inválido (JSON malformado)", 400)
        else:
            historico_interno = None

        # Payload normalizado para o módulo de análise
        payload = {
            "aluno": data.get("aluno"),
            "historico": data.get("historico"),
            "historico_interno": historico_interno,
            "grade": data.get("grade"),
            "candidato": data.get("candidato"),
            "id_analise": data.get("id_analise"),
            "usuario_id": data.get("usuario_id")
        }

        # Validações obrigatórias
        if not payload['historico'] and not payload['historico_interno']:
            return err("Campo 'historico' ou 'historico_interno' é obrigatório", 400)
        if not payload['aluno']:
            return err("Campo 'aluno' é obrigatório", 400)
        if not payload['grade']:
            return err("Campo 'grade' é obrigatório", 400)
        if not payload['candidato']:
            return err("Campo 'candidato' é obrigatório", 400)
        if not payload['id_analise']:
            return err("Campo 'id_analise' é obrigatório", 400)
        if not payload['usuario_id']:
            return err("Campo 'usuario_id' é obrigatório", 400)

        # Remove estruturas não serializáveis (ex: set)
        payload = convert_sets(payload)

        # Execução principal da análise
        result = convert_sets(ah.main(payload))

        # O integrador não depende do retorno,
        # apenas do efeito colateral (insert/update no banco)
        if result['status'] == 'sucesso':
            return JSONResponse(content={
                "status": "processado",
                "resultado": convert_sets(result['detalhes'])
            }, status_code=200)

        elif result['status'] == 'erro':
            print(f"Não processou: {result}")
            return JSONResponse(content={
                "status": "nao processado",
                "resultado": convert_sets(result['detalhes']),
                "payload": payload
            }, status_code=200)

        # Caso não esperado
        print(f"Erro ao processar histórico {result}")
        return err("Erro ao processar histórico", 200, {
            "detail": convert_sets(result.get('detalhes'))
        })

    except Exception as e:
        return err("Erro interno", 500, {"detail": str(e)})



def convert_sets(obj):
    """
    Converte estruturas não serializáveis (ex: set)
    em tipos compatíveis com JSON.

    Usado antes de retornar respostas ou salvar logs.
    """

    if isinstance(obj, set):
        return list(obj)
    elif isinstance(obj, dict):
        return {k: convert_sets(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_sets(i) for i in obj]
    else:
        return obj


if __name__ == "__main__":
    # debug=False para evitar reload duplo e execução duplicada
    uvicorn.run(app, host="0.0.0.0", port=5010)
