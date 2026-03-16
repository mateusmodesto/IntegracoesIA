"""
Gerenciador de Banco de Dados - GerarPeticao
Operacoes especificas de templates de documentos juridicos.
"""

from typing import Dict, Any, List, Optional

from shared.database import BaseDatabaseManager


class DatabaseManager(BaseDatabaseManager):

    def select_data_atual(self) -> str:
        """Retorna a data atual do servidor SQL no formato dd/MM/yyyy."""
        resultado = self.fetch_one("SELECT FORMAT(GETDATE(), 'dd/MM/yyyy') AS DataBrasil")
        return resultado["DataBrasil"] if resultado else ""
