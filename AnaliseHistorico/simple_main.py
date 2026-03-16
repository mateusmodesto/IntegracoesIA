from typing import Any

from shared.config import DATABASE_CONFIG, get_logger

from . import LerHistorico as lerHistorico
from . import database_manager as db_manager

logger = get_logger(__name__)


class AnaliseHistorico:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.gemini = lerHistorico.Gemini()
        self.db = db_manager.DatabaseManager(DATABASE_CONFIG)
        self.payload = payload

    def processar_historico(self, grade: dict[str, Any]) -> dict[str, Any]:
        logger.info("Iniciando processamento de historico para analise %s", self.payload.get("id_analise"))

        id_reg = self.db.inserir_analise_historico(
            self.payload['id_analise'],
            self.payload['usuario_id']
        )

        if not id_reg or not isinstance(id_reg, dict) or 'buscaId' not in id_reg:
            return {
                "status": "erro",
                "mensagem": "Falha ao iniciar analise no banco de dados",
                "detalhes": "inserir_analise_historico retornou valor invalido"
            }

        busca_id = id_reg['buscaId']

        try:
            historico = self.payload.get("historico")
            if not historico:
                self.db.anular_validacao(busca_id, "Historico nao informado")
                return self._erro("Historico e obrigatorio", None)

            resultado = self.gemini.transformToJson(historico=historico, grade=grade)

            if not isinstance(resultado, dict):
                self.db.anular_validacao(busca_id, f"Resultado invalido: tipo={type(resultado).__name__}")
                return self._erro("Resposta invalida do servico de IA", resultado)

            if self._tem_erro(resultado):
                motivo = resultado.get("Motivo") or self._extrair_motivo_erro(resultado)
                self.db.anular_validacao(busca_id, f"Erro na IA: {motivo}")
                return self._erro("Erro ao analisar o historico", resultado)

            comparacao = resultado.get("comparacao", {})
            if isinstance(comparacao, dict):
                comparacao = comparacao.get("comparacao_disciplinas", [])
            if not isinstance(comparacao, list):
                comparacao = []

            if len(comparacao) == 0:
                self.db.anular_validacao(busca_id, "Resposta sem comparacao")
                return self._erro("Nao ha comparacao do historico ou estrutura invalida", resultado)

            execucao = self.db.salvar_analise_historico(busca_id, resultado, grade)
            if execucao.get("status") == "sucesso":
                logger.info("Processamento concluido com sucesso para analise %s", self.payload.get("id_analise"))
                return {
                    "status": "sucesso",
                    "mensagem": "Analise processada e salva com sucesso",
                    "detalhes": {
                        "extracao": resultado.get("extracao"),
                        "comparacao": comparacao,
                    }
                }

            self.db.anular_validacao(busca_id, "Erro ao salvar analise no banco de dados")
            return self._erro("Erro ao salvar analise no banco de dados", execucao)

        except Exception as e:
            logger.error("Erro inesperado ao processar historico: %s", e, exc_info=True)
            self.db.anular_validacao(busca_id, f"Erro no processamento: {e}")
            return self._erro("Erro inesperado ao processar historico", str(e))

    def _tem_erro(self, resultado: dict[str, Any]) -> bool:
        if resultado.get("Erro") is True:
            return True
        extracao = resultado.get("extracao")
        if isinstance(extracao, dict) and extracao.get("Erro"):
            return True
        comparacao = resultado.get("comparacao")
        if isinstance(comparacao, dict) and comparacao.get("Erro"):
            return True
        return False

    def _extrair_motivo_erro(self, resultado: dict[str, Any]) -> str:
        for chave in ("extracao", "comparacao"):
            sub = resultado.get(chave)
            if isinstance(sub, dict) and sub.get("Erro"):
                return sub.get("Motivo", "Motivo desconhecido")
        return "Erro desconhecido"

    def _erro(self, mensagem: str, detalhes: Any) -> dict[str, Any]:
        return {"status": "erro", "mensagem": mensagem, "detalhes": detalhes}

    def buscarGrade(self) -> dict[str, Any]:
        resultado = self.db.fetch_all(
            """
            SELECT
                ID, ID_CANDIDATO, CURRICULO, SERIE,
                COD_DISCIPLINA, DISCIPLINA, CH,
                NOTA_EXT, DISCIPLINA_EXT,
                DISPENSA, DEPENDENCIA, ADAPTACAO,
                REGULAR, ANO, SEMESTRE
            FROM dtb_anchieta_prod.dbo.ANC_TRANSF_ANALISE_ALUNO
            WHERE CURRICULO = ?
              AND ID_CANDIDATO = TRY_CAST(? AS INT)
            """,
            [self.payload['grade'], self.payload['candidato']]
        )

        json_novas: dict[str, Any] = {}

        for item in resultado:
            nome = item.get("DISCIPLINA")
            if not nome:
                continue

            chave = nome.strip().upper()

            json_novas[chave] = {
                "codigo": item.get("COD_DISCIPLINA"),
                "carga_horaria": item.get("CH"),
                "semestre": item.get("SEMESTRE"),
                "serie": item.get("SERIE"),
                "regular": item.get("REGULAR"),
                "dependencia": item.get("DEPENDENCIA"),
                "dispensa": item.get("DISPENSA"),
            }

        return json_novas


def main(payload: dict[str, Any]) -> dict[str, Any]:
    analise = AnaliseHistorico(payload)
    grade = analise.buscarGrade()
    return analise.processar_historico(grade)
