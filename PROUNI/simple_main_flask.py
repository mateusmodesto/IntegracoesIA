"""
Processador de documentos PROUNI.

Recebe payload da API, chama Gemini para validacao/extracao
e grava resultado no banco.
"""

from typing import Dict, Any

from .LerDocumentoClass import Gemini
from .database_manager import DatabaseManager
from shared.config import get_logger

logger = get_logger(__name__)


class DocumentProcessorWeb:
    """Processa um documento PROUNI: valida via IA e grava no banco."""

    def __init__(self, database_config: Dict[str, Any]):
        self.db_manager = DatabaseManager(database_config)
        self.gemini = Gemini()

    def process_document(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa um documento individual.

        Args:
            payload: Dict com 'arquivo', 'pessoa' e 'tipo_documento'.

        Returns:
            Dict com status do processamento.
        """
        url_doc = payload["arquivo"]
        tipo_doc = payload["tipo_documento"]

        api_resposta = None

        try:
            api_resposta = self.gemini.analisarDocumento(url=url_doc, tipo_doc=tipo_doc)

            if api_resposta.get("Erro"):
                return {
                    "status": "error",
                    "message": "Erro ao se conectar com a IA",
                    "api_resposta": api_resposta,
                }

            resposta_banco = self.db_manager.update_documento_prouni(
                dados=payload, resposta_IA=api_resposta
            )

            return {
                "status": "sucesso",
                "banco": resposta_banco,
                "api_resposta": api_resposta,
            }

        except Exception as e:
            is_timeout = (
                "timeout" in str(e).lower()
                or "504" in str(e)
                or "endpoint request timed out" in str(e).lower()
            )

            if is_timeout:
                logger.warning(f"Timeout ao processar documento: {tipo_doc}")
                return {"status": "timeout", "retry_needed": True}

            logger.error(f"Erro ao processar documento {tipo_doc}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "api_resposta": api_resposta,
                "retry_needed": False,
            }


def main(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ponto de entrada chamado pela API.

    Args:
        payload: Dict com 'arquivo', 'pessoa' e 'tipo_documento'.

    Returns:
        Resultado do processamento.
    """
    from shared.config import DATABASE_CONFIG

    processor = DocumentProcessorWeb(DATABASE_CONFIG)

    try:
        return processor.process_document(payload)
    except Exception as e:
        logger.error(f"Erro fatal no processamento PROUNI: {e}")
        return {"status": "error", "mensagem": str(e)}
