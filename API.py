"""
API Flask principal - Sistema de Processamento de Documentos com IA.

Endpoints:
    POST /validar           - Validacao de documentos de alunos
    POST /PROUNI            - Validacao de documentos PROUNI
    POST /analiseHistorico  - Analise de historico escolar (async)
    POST /documentos/gerar  - Geracao de documentos juridicos
    POST /gerar-pdf         - Geracao de PDF a partir de HTML
    POST /sistema_compras/comparar  - Comparacao de planilhas
    GET  /sistema_compras/download  - Download do resultado
"""

import os
import uuid
import tempfile
import threading
from io import BytesIO
from typing import Any, Dict, Optional, Tuple

from flask import Flask, Response, request, jsonify, send_file
from flask_cors import CORS

from shared.config import get_logger, FLASK_PORT

logger = get_logger(__name__)

# ── App Flask ─────────────────────────────────────────────────────────────

app = Flask(__name__)

CORS(app, resources={r"/*": {
    "origins": "*",
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"],
}})

DOCS_OUTPUT_DIR = os.path.join(tempfile.gettempdir(), "docs_juridicos")
os.makedirs(DOCS_OUTPUT_DIR, exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────────────────

def _parse_json_body() -> Optional[Dict[str, Any]]:
    """Tenta extrair JSON do body da request. Retorna None se invalido."""
    try:
        data = request.get_json(force=True)
    except Exception:
        data = None
    return data if isinstance(data, dict) else None


def _validate_required(data: Dict[str, Any], campos: list[str]) -> Optional[Tuple[Response, int]]:
    """Valida campos obrigatorios. Retorna resposta de erro ou None se tudo ok."""
    for campo in campos:
        if data.get(campo) is None:
            return _err(f"Campo '{campo}' e obrigatorio", 400)
    return None


def _err(msg: str, code: int = 400, extra: Optional[Dict[str, Any]] = None) -> Tuple[Response, int]:
    """Retorna JSON de erro padronizado."""
    payload: Dict[str, Any] = {"status": "erro", "msg": msg}

    if extra:
        for k, v in extra.items():
            if isinstance(v, (dict, list, str, int, float, bool)) or v is None:
                payload[k] = v
            else:
                payload[k] = str(v)

    return jsonify(payload), code


def _format_result(result: Dict[str, Any], payload: Optional[Dict[str, Any]] = None) -> Tuple[Response, int]:
    """Formata resposta padronizada baseada no status do resultado."""
    status = result.get("status", "")

    if status == "sucesso":
        return jsonify({"status": "processado", "resultado": result}), 200

    if status in ("error", "timeout"):
        body: Dict[str, Any] = {"status": "nao processado", "resultado": result}
        if payload:
            body["payload"] = payload
        return jsonify(body), 200

    return _err("Erro ao processar documento", 200, {"detail": result})


def _convert_sets(obj: Any) -> Any:
    """Converte sets para listas (JSON nao suporta set)."""
    if isinstance(obj, set):
        return list(obj)
    if isinstance(obj, dict):
        return {k: _convert_sets(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_sets(i) for i in obj]
    return obj


# ── Endpoints ─────────────────────────────────────────────────────────────

@app.route("/validar", methods=["POST"])
def validar():
    """Valida documentos de alunos (RG, CPF, CNH, certidoes, etc)."""
    import LeituraDocumentos.simple_main_flask as sp

    try:
        data = _parse_json_body()
        if data is None:
            return _err("JSON invalido ou ausente", 400)

        payload = {
            "arquivo": data.get("arquivo"),
            "aluno": data.get("aluno"),
            "posicao": data.get("posicao"),
            "usuario": data.get("usuario"),
            "curso_entrega": data.get("curso_entrega"),
        }

        erro = _validate_required(payload, ["arquivo", "aluno", "posicao", "usuario", "curso_entrega"])
        if erro:
            return erro

        result = sp.main(payload)
        return _format_result(result, payload)

    except Exception as e:
        logger.error(f"Erro interno em /validar: {e}", exc_info=True)
        return _err("Erro interno", 500, {"detail": str(e)})


@app.route("/PROUNI", methods=["POST"])
def prouni():
    """Valida documentos do programa PROUNI."""
    import PROUNI.simple_main_flask as sp

    try:
        data = _parse_json_body()
        if data is None:
            return _err("JSON invalido ou ausente", 400)

        erro = _validate_required(data, ["arquivo", "pessoa", "tipo_documento"])
        if erro:
            return erro

        result = sp.main(data)
        return _format_result(result, data)

    except Exception as e:
        logger.error(f"Erro interno em /PROUNI: {e}", exc_info=True)
        return _err("Erro interno", 500, {"detail": str(e)})


@app.route("/analiseHistorico", methods=["POST"])
def analise_historico():
    """
    Analisa historico escolar para dispensa de disciplinas.

    Processamento assincrono: retorna 200 imediatamente.
    O resultado e gravado na tabela ANC_VALIDA_DISPENSA.
    """
    from AnaliseHistorico import simple_main as ah

    try:
        data = _parse_json_body()
        if data is None:
            return _err("JSON invalido ou ausente", 400)

        payload = {
            "aluno": data.get("aluno"),
            "historico": data.get("historico"),
            "grade": data.get("grade"),
            "candidato": data.get("candidato"),
            "id_analise": data.get("id_analise"),
            "usuario_id": data.get("usuario_id"),
            "tipo_historico": data.get("tipo_historico"),
        }

        erro = _validate_required(payload, ["historico", "aluno", "grade", "candidato", "id_analise", "usuario_id"])
        if erro:
            return erro

        payload = _convert_sets(payload)

        def _processar():
            try:
                result = ah.main(payload)
                logger.info(f"analiseHistorico concluido id_analise={payload['id_analise']}: {result.get('status')}")
            except Exception as e:
                logger.error(f"analiseHistorico erro id_analise={payload['id_analise']}: {e}", exc_info=True)

        threading.Thread(target=_processar, daemon=True).start()

        return jsonify({
            "status": "aceito",
            "mensagem": "Analise recebida e sendo processada. Consulte a tabela ANC_VALIDA_DISPENSA.",
        }), 200

    except Exception as e:
        logger.error(f"Erro interno em /analiseHistorico: {e}", exc_info=True)
        return _err("Erro interno", 500, {"detail": str(e)})


@app.route("/documentos/gerar", methods=["POST"])
def gerar_documento():
    """Gera documento juridico (.docx) a partir de template do banco."""
    from GerarPeticao.agente_rag import AgenteJuridico, DB_CONFIG

    try:
        data = _parse_json_body()
        if data is None:
            return _err("JSON invalido ou ausente", 400)

        tipo_documento = data.get("tipo_documento")
        secoes = data.get("secoes")
        dados = data.get("dados")

        if not tipo_documento:
            return _err("Campo 'tipo_documento' e obrigatorio", 400)
        if not dados or not isinstance(dados, dict):
            return _err("Campo 'dados' e obrigatorio e deve ser um objeto", 400)

        # Flatten dados aninhados {id: {var: valor}} -> {var: valor}
        dados_flat = {}
        for key, value in dados.items():
            if isinstance(value, dict):
                dados_flat.update(value)
            else:
                dados_flat[key] = value

        # Extrai textos das subcategorias ordenados
        textos_secoes = []
        if secoes and isinstance(secoes, list):
            secoes_ordenadas = sorted(secoes, key=lambda s: s.get("ordem", 0))
            textos_secoes = [s["subcategoria"] for s in secoes_ordenadas if s.get("subcategoria")]

        agente = AgenteJuridico(db_config=DB_CONFIG)
        doc_id = uuid.uuid4().hex[:8]
        nome_arquivo = f"{doc_id}.docx"
        docx_path = os.path.join(DOCS_OUTPUT_DIR, nome_arquivo)

        agente.criar_documento(
            tipo_documento=tipo_documento,
            subcategorias_texto=textos_secoes,
            output_path=docx_path,
            dados=dados_flat,
        )

        return send_file(
            docx_path,
            as_attachment=True,
            download_name=nome_arquivo,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    except ValueError as e:
        return _err(str(e), 400)
    except Exception as e:
        logger.error(f"Erro interno em /documentos/gerar: {e}", exc_info=True)
        return _err("Erro interno na geracao do documento", 500, {"detail": str(e)})


# ── Gerador de PDF ────────────────────────────────────────────────────────

@app.route("/gerar-pdf", methods=["POST"])
def gerar_pdf():
    """Gera PDF a partir de HTML e envia para webhook N8N."""
    from GerarEbook.gerar_pdf import _gerar_pdf_sync, WEBHOOK_SALVAR

    try:
        data = _parse_json_body()
        if data is None:
            return _err("JSON invalido ou ausente", 400)

        # Aceita array (formato N8N) ou objeto direto
        if isinstance(data, list):
            data = data[0]

        html_content = data.get("html")
        if not html_content:
            return _err("Campo 'html' e obrigatorio", 400)

        logger.info(f"Recebido HTML ({len(html_content)} chars). Gerando PDF...")

        pdf_bytes = _gerar_pdf_sync(html_content)

        logger.info(f"PDF gerado: {len(pdf_bytes) / 1024:.1f} KB")

        # Envia o PDF para o webhook
        import httpx
        with httpx.Client(timeout=120) as client:
            resp = client.post(
                WEBHOOK_SALVAR,
                files={"file": ("ebook.pdf", pdf_bytes, "application/pdf")},
            )

        logger.info(f"Webhook status: {resp.status_code}")

        return jsonify({
            "sucesso": True,
            "pdf_tamanho_kb": round(len(pdf_bytes) / 1024, 1),
            "webhook_status": resp.status_code,
            "webhook_resposta": resp.text[:500],
        }), 200

    except Exception as e:
        logger.error(f"Erro interno em /gerar-pdf: {e}", exc_info=True)
        return _err("Erro interno", 500, {"detail": str(e)})


# ── Comparador de Planilhas ───────────────────────────────────────────────

@app.route("/sistema_compras/comparar", methods=["POST"])
def comparar_route():
    """Compara planilhas de ordem de compra."""
    try:
        from ComparadorTabela.processamento import processar
    except ImportError:
        return _err("Modulo ComparadorTabela nao disponivel", 501)

    if "conta_certa" not in request.files:
        return jsonify({"erro": "Envie o arquivo conta_certa"}), 400

    files_comparar = [f for f in request.files.getlist("conta_comparar") if f.filename]
    if not files_comparar:
        files_comparar = [
            f for key, f in request.files.items()
            if key.startswith("conta_comparar") and f.filename
        ]
    if not files_comparar:
        return jsonify({"erro": "Envie pelo menos um arquivo conta_comparar"}), 400

    file_certa = request.files["conta_certa"]
    tolerancia = float(request.form.get("tolerancia", 1.0))

    resultado = processar(file_certa, files_comparar, tolerancia)

    app.config["ULTIMO_RESULTADO"] = resultado["xlsx_bytes"]

    return jsonify({
        "total": resultado["total"],
        "encontrados": resultado["encontrados"],
        "sem_match": resultado["sem_match"],
        "dados": resultado["dados"],
    })


@app.route("/sistema_compras/download", methods=["GET"])
def download():
    """Download do resultado da ultima comparacao."""
    dados = app.config.get("ULTIMO_RESULTADO")
    if dados is None:
        return jsonify({"erro": "Nenhum resultado disponivel"}), 404

    return send_file(
        BytesIO(dados),
        as_attachment=True,
        download_name="planilha_comparada.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ── Entrypoint ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=False)
