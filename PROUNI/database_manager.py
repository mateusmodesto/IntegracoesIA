#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerenciador de Banco de Dados - Sistema de Processamento de Documentos
Gerencia conexões e operações com SQL Server
"""

import json
from typing import Dict, Any, List, Optional, Union, Tuple
import pyodbc
from contextlib import contextmanager


class DatabaseManager:
    """
    Classe para gerenciar conexões e operações com o banco de dados SQL Server
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa o gerenciador de banco de dados
        
        Args:
            config: Configurações de conexão com o banco
        """
        self.config = config
        self.connection_string = self._build_connection_string()
    
    def _build_connection_string(self) -> str:
        """
        Constrói a string de conexão com o SQL Server
        
        Returns:
            String de conexão formatada
        """
        return (
            f"DRIVER=ODBC Driver 17 for SQL Server;"
            f"SERVER={self.config['host']},{self.config.get('port', 1433)};"
            f"DATABASE={self.config['database']};"
            f"UID={self.config['user']};"
            f"PWD={self.config['password']};"
            "Encrypt=yes;"
            "TrustServerCertificate=yes;"
            f"Trusted_Connection=no;"
        )
    
    @contextmanager
    def get_connection(self):
        """
        Context manager para gerenciar conexões com o banco
        
        Yields:
            Conexão ativa com o banco de dados
        """
        connection = None
        try:
            connection = pyodbc.connect(self.connection_string)
            yield connection
        except Exception as e:
            if connection:
                connection.rollback()
            raise e
        finally:
            if connection:
                connection.close()
    
    def execute_query(self, query: str, params: Optional[Union[Dict[str, Any], Tuple, List]] = None) -> int:
        """
        Executa uma query SQL e retorna o número de linhas afetadas

        Args:
            query: Query SQL a ser executada
            params: Parâmetros da query (dict, tuple ou list)

        Returns:
            Número de linhas afetadas
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                if params is not None:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                conn.commit()
                return cursor.rowcount
            except Exception as e:
                conn.rollback()
                raise e
    
    def fetch_one(self, query: str, params: Optional[Union[Dict[str, Any], Tuple, List]] = None) -> Optional[Dict[str, Any]]:
        """
        Executa uma query e retorna um único resultado

        Args:
            query: Query SQL a ser executada
            params: Parâmetros da query (dict, tuple ou list)

        Returns:
            Primeiro resultado da query ou None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params is not None:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            columns = [column[0] for column in cursor.description] if cursor.description else []
            row = cursor.fetchone()

            if row:
                return dict(zip(columns, row))
            return None
    
    def fetch_all(self, query: str, params: Optional[Union[Dict[str, Any], Tuple, List]] = None) -> List[Dict[str, Any]]:
        """
        Executa uma query e retorna todos os resultados

        Args:
            query: Query SQL a ser executada
            params: Parâmetros da query (dict, tuple ou list)

        Returns:
            Lista com todos os resultados da query
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params is not None:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            columns = [column[0] for column in cursor.description] if cursor.description else []
            rows = cursor.fetchall()

            return [dict(zip(columns, row)) for row in rows]
    
    
    
    def update_documento_prouni(self, aluno: str, resposta_IA: Union[str, Dict[str, Any]], tipo_doc: str, url_doc: str) -> int:
        """
        Atualiza dados do candidato

        Args:
            aluno: Código do aluno
            resposta_IA: Resposta da IA para o aluno (string ou dict que será convertido para JSON)
            tipo_doc: Tipo do documento
            url_doc: URL do documento

        Returns:
            Número de linhas afetadas
        """
        if not resposta_IA:
            return 0

        # Garante que resposta_IA é sempre uma string para o pyodbc
        if not isinstance(resposta_IA, str):
            resposta_IA = json.dumps(resposta_IA, ensure_ascii=False, default=str)

        query = """
            UPDATE dtb_anchieta_prod.dbo.ANC_SOLICITACAO_BOLSA_ANEXO
            SET Resposta_IA = ?
            WHERE CAMINHO = ?
        """

        params = (resposta_IA, str(url_doc))

        return self.execute_query(query, params)
