"""
Gerenciador de Banco de Dados - AnaliseHistorico
Operacoes especificas de analise de historico escolar e dispensas.
"""

import json
from typing import Dict, Any

from shared.database import BaseDatabaseManager
from shared.config import get_logger

logger = get_logger(__name__)


class DatabaseManager(BaseDatabaseManager):

    def inserir_analise_historico(self, id_analise, usuario_id):
        try:
            query = """
                INSERT INTO DTB_ANCHIETA_PROD.dbo.ANC_VALIDA_DISPENSA
                    (FK_ID_ANALISE, DT_VALIDACAO, USUARIO, ACEITO, ATIVO)
                OUTPUT INSERTED.ID
                VALUES (?, GETDATE(), ?, 'N', 1)
            """
            execucao = self.execute_insert_returning_id(query, (id_analise, usuario_id))

            return {
                "status": "sucesso",
                "mensagem": "Analise salva com sucesso",
                "buscaId": execucao
            }

        except Exception as e:
            return {
                "status": "erro",
                "mensagem": "Erro ao salvar analise no banco de dados",
                "detalhes": str(e)
            }

    def anular_validacao(self, id, erro):
        try:
            erro_str = str(erro) if not isinstance(erro, str) else erro
            if len(erro_str) > 4000:
                erro_str = erro_str[:3997] + "..."

            query = """
                UPDATE DTB_ANCHIETA_PROD.dbo.ANC_VALIDA_DISPENSA
                SET ATIVO = 0,
                    motivo_erro = ?
                WHERE ID = ?
            """
            params = (erro_str, id)
            execucao = self.execute_query(query, params)

            if execucao > 0:
                return {
                    "status": "sucesso",
                    "mensagem": "Analise anulada com sucesso"
                }
            else:
                return {
                    "status": "erro",
                    "mensagem": "Nenhuma linha foi afetada ao anular a analise",
                    "detalhes": str(execucao)
                }

        except Exception as e:
            return {
                "status": "erro",
                "mensagem": "Erro ao anular o processamento da analise no banco de dados",
                "detalhes": str(e)
            }

    def salvar_analise_historico(self, id, resultado: Dict[str, Any], grade):
        try:
            query = """
                UPDATE DTB_ANCHIETA_PROD.dbo.ANC_VALIDA_DISPENSA
                SET GRADE_ATUAL = ?,
                    GRADE_CURSADA = ?,
                    RESPOSTA_IA = ?
                WHERE ID = ?
            """

            params = (
                json.dumps(grade, ensure_ascii=False),
                json.dumps(resultado['extracao'], ensure_ascii=False),
                json.dumps(resultado['comparacao'], ensure_ascii=False),
                id
            )

            execucao = self.execute_query(query, params)

            if execucao > 0:
                return {
                    "status": "sucesso",
                    "mensagem": "Analise processada e salva com sucesso"
                }
            else:
                return {
                    "status": "erro",
                    "mensagem": "Nenhuma linha foi afetada ao salvar a analise",
                    "detalhes": str(execucao)
                }

        except Exception as e:
            return {
                "status": "erro",
                "mensagem": "Erro ao salvar o processamento da analise no banco de dados",
                "detalhes": str(e)
            }
