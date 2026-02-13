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

        # Extrai is_valid antes de serializar para string
        if isinstance(resposta_IA, dict):
            is_valid = 'S' if resposta_IA.get('validacao', {}).get('is_valid') else 'N'
            resposta_IA = json.dumps(resposta_IA, ensure_ascii=False, default=str)
        else:
            is_valid = None

        query = """
            INSERT INTO DTB_ANCHIETA_PROD.DBO.ANC_SOLICITACAO_BOLSA_ANEXO_VALIDA_DOC
            SELECT CAST(ID AS INT) AS ID, ? AS RESPOSTA_API, ? AS TITULAR, ? AS VALIDO, GETDATE() AS DATA
            FROM DTB_ANCHIETA_PROD.DBO.ANC_SOLICITACAO_BOLSA_ANEXO
            WHERE CAMINHO = ?
        """

        params = (resposta_IA, None, is_valid, str(url_doc))

        return self.execute_query(query, params)
    
    def buscar_documentos_pendentes(self) -> List[Dict[str, Any]]:
        """
        Busca documentos pendentes para processamento

        Returns:
            Lista de documentos pendentes
        """
        query = """
            SELECT B.*
            FROM DTB_ANCHIETA_PROD.DBO.ANC_SOLICITACAO_BOLSA A
            JOIN DTB_ANCHIETA_PROD.DBO.ANC_SOLICITACAO_BOLSA_ANEXO B
                ON A.ID = B.ID_SOLICITACAO
            WHERE A.nome NOT LIKE '%teste%'
            AND A.ano = '2026'
            AND A.TIPO_SOLICITACAO <> 'CEU'
            AND A.JUSTIFICATIVA IS NOT NULL
            AND A.APROVACAO IN ('2','3','4')
            AND B.TIPO_DOCUMENTO IN (
                    'CERT_CONCLUSAO_CURSO',
                    'CERTIDAO_CASAMENTO',
                    'CERTIDAO_NASC',
                    'Carteira de Trabalho',
                    'ATUALIZADO',
                    'CLT',
                    'COMPROVANTE DE RESIDENCIA',
                    'CPF',
                    'ctps',
                    'DECLARAÇÃO DE AUSENCIA',
                    'DECLARAÇÃO DE AUSENCIA DE RENDA',
                    'DECLARAÇÃO DE CONCLUSÃO',
                    'Declaração de Renda Informal',
                    'DECLARACAO_AUSENCIA_RENDA',
                    'DECLARACAO_AUTONOMO',
                    'DECLARACAO_RENDA_AUTONOMO',
                    'DECLARACAO_RENDA_INFORMAL',
                    'EXTRATO_1_RENDA_AUTONOMO',
                    'EXTRATO_1_RENDA_INFORMAL',
                    'EXTRATO_2_RENDA_AUTONOMO',
                    'EXTRATO_2_RENDA_INFORMAL',
                    'EXTRATO_3_RENDA_AUTONOMO',
                    'EXTRATO_3_RENDA_INFORMAL',
                    'EXTRATO_COMPROBATORIO_1',
                    'EXTRATO_COMPROBATORIO_2',
                    'EXTRATO_COMPROBATORIO_3',
                    'EXTRATO_RENDA_AUTONOMO_1',
                    'EXTRATO_RENDA_AUTONOMO_2',
                    'EXTRATO_RENDA_AUTONOMO_3',
                    'Extratos1',
                    'HISTORICO',
                    'HOLERITE_1',
                    'HOLERITE_2',
                    'HOLERITE_3',
                    'HOLERITE_4',
                    'HOLERITE_5',
                    'HOLERITE_6',
                    'holerites',
                    'PRO-LABORE',
                    'OUTROS_DOCUMENTOS',
                    'RESIDENCIA',
                    'RG',
                    'RG_VERSO',
                    'PAGINA_FOTO',
                    'PAGINA_QUALI_CIVIL',
                    'PAGINA_ULTIMO_CONTRATO',
                    'PAGINA_BRANCO',
                    'PAGINA_QUALIFICACAO'
            );

        """
        return self.fetch_all(query)