"""
Gerenciador de Banco de Dados - PROUNI.

Operacoes de gravacao de validacao de documentos e
marcacao de documentos entregues para alunos/familiares.
"""

import json
from typing import Dict, Any, Optional, Union

from shared.database import BaseDatabaseManager
from shared.config import get_logger

logger = get_logger(__name__)


class DatabaseManager(BaseDatabaseManager):
    """Operacoes de banco especificas do modulo PROUNI."""

    def update_documento_prouni(
        self,
        dados: Dict[str, Any],
        resposta_IA: Union[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Grava resultado da validacao IA e, se valido, marca documento como entregue.

        Args:
            dados: Payload original com 'arquivo', 'pessoa', 'tipo_documento'.
            resposta_IA: Resposta da IA (dict ou JSON string).

        Returns:
            Dict com 'update_valida' e 'update_entregue'.
        """
        if not resposta_IA:
            return {"update_valida": 0, "update_entregue": None}

        # Extrai is_valid antes de serializar
        if isinstance(resposta_IA, dict):
            is_valid = "S" if resposta_IA.get("validacao", {}).get("is_valid") else "N"
            resposta_IA_json = json.dumps(resposta_IA, ensure_ascii=False, default=str)
        else:
            is_valid = None
            resposta_IA_json = resposta_IA

        # 1. Insere registro de validacao
        query_valida = """
            INSERT INTO DTB_ANCHIETA_PROD.DBO.ANC_SOLICITACAO_BOLSA_ANEXO_VALIDA_DOC
            SELECT TOP 1
                CAST(ID AS INT) AS ID,
                ? AS RESPOSTA_API,
                ? AS TITULAR,
                ? AS VALIDO,
                GETDATE() AS DATA
            FROM DTB_ANCHIETA_PROD.DBO.ANC_SOLICITACAO_BOLSA_ANEXO
            WHERE CAMINHO = ?
            ORDER BY data_insercao DESC
        """
        params_valida = (resposta_IA_json, None, is_valid, str(dados["arquivo"]))
        update_valida = self.execute_query(query_valida, params_valida)

        # 2. Se valido, marca documento como entregue
        update_entregue = None

        if is_valid == "S":
            relacao = self.verifica_relacao(dados)

            if relacao is None:
                logger.warning(f"Nenhuma relacao encontrada para pessoa={dados.get('pessoa')}")
            else:
                update_entregue = self._inserir_doc_entregue(relacao, dados["tipo_documento"])

        return {"update_valida": update_valida, "update_entregue": update_entregue}

    def verifica_relacao(self, dados: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Verifica se o documento pertence a um aluno ou familiar.

        Args:
            dados: Payload com 'pessoa'.

        Returns:
            Dict com 'ID_SOLICITACAO', 'CATEGORIA', 'ID_FAMILIAR' ou None.
        """
        query = """
            SELECT DISTINCT
                b.ID_SOLICITACAO,
                IIF(A.PESSOA != B.PESSOA, 'FAMILIAR', 'ALUNO') AS CATEGORIA,
                C.ID AS ID_FAMILIAR
            FROM DTB_ANCHIETA_PROD.DBO.ANC_SOLICITACAO_BOLSA A
            JOIN DTB_ANCHIETA_PROD.DBO.ANC_SOLICITACAO_BOLSA_ANEXO B
                ON A.ID = B.ID_SOLICITACAO
            LEFT JOIN DTB_ANCHIETA_PROD.DBO.ANC_SOLICITACAO_BOLSA_FAMILIARES C
                ON C.ID_SOLICITACAO = A.ID AND C.PESSOA = B.PESSOA
            WHERE B.PESSOA = ?
        """
        return self.fetch_one(query, (dados["pessoa"],))

    def _inserir_doc_entregue(
        self, relacao: Dict[str, Any], tipo_documento: str
    ) -> int:
        """
        Insere registro de documento entregue (aluno ou familiar).

        Usa INSERT ... WHERE NOT EXISTS para evitar duplicatas.
        """
        if relacao["CATEGORIA"] == "ALUNO":
            tabela = "ANC_SOLICITACAO_BOLSA_ALUNO_DOC_ENTREGUE"
            coluna_id = "ID_SOLICITACAO"
            valor_id = relacao["ID_SOLICITACAO"]
        else:
            tabela = "ANC_SOLICITACAO_BOLSA_FAMILIARES_DOC_ENTREGUE"
            coluna_id = "ID_FAMILIAR"
            valor_id = relacao["ID_FAMILIAR"]

        query = f"""
            INSERT INTO DTB_ANCHIETA_PROD..{tabela} ({coluna_id}, TIPO_DOC)
            SELECT ?, ?
            WHERE NOT EXISTS (
                SELECT 1
                FROM DTB_ANCHIETA_PROD..{tabela}
                WHERE {coluna_id} = ?
                AND TIPO_DOC = ?
            )
        """
        params = (valor_id, tipo_documento, valor_id, tipo_documento)
        return self.execute_query(query, params)
