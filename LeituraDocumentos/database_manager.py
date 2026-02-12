#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerenciador de Banco de Dados - Sistema de Processamento de Documentos
Gerencia conexões e operações com SQL Server
"""

import json
from typing import Dict, Any, List, Optional
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
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> int:
        """
        Executa uma query SQL e retorna o número de linhas afetadas
        
        Args:
            query: Query SQL a ser executada
            params: Parâmetros da query
            
        Returns:
            Número de linhas afetadas
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                conn.commit()
                return cursor.rowcount
            except Exception as e:
                conn.rollback()
                raise e
    
    def fetch_one(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Executa uma query e retorna um único resultado
        
        Args:
            query: Query SQL a ser executada
            params: Parâmetros da query
            
        Returns:
            Primeiro resultado da query ou None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            columns = [column[0] for column in cursor.description] if cursor.description else []
            row = cursor.fetchone()
            
            if row:
                return dict(zip(columns, row))
            return None
    
    def fetch_all(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Executa uma query e retorna todos os resultados
        
        Args:
            query: Query SQL a ser executada
            params: Parâmetros da query
            
        Returns:
            Lista com todos os resultados da query
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            columns = [column[0] for column in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            
            return [dict(zip(columns, row)) for row in rows]
    
    def delete_document_validation(self, id_doc: str, tipos_documento: List[str]) -> None:
        """
        Remove registros de validação de documentos existentes
        
        Args:
            id_doc: ID do documento
            tipos_documento: Lista de tipos de documento a serem removidos
        """
        if not tipos_documento:
            return
        
        # Constrói a condição IN para os tipos de documento
        placeholders = ','.join(['?' for _ in tipos_documento])
        query = f"""
        DELETE FROM ANCHI_DOCUMENTOS_ENTREGUES_VALIDA 
        WHERE ID_DOCUMENTOS_ENTREGUES = ? 
        AND TIPO_DOCUMENTO IN ({placeholders})
        """
        
        params = [id_doc] + tipos_documento
        self.execute_query(query, params)
    
    def insert_document_validation(self, id_doc: str, aluno: str, tipo_documento: str, 
                                 response: Dict[str, Any], valido: str, titular: str) -> None:
        """
        Insere um novo registro de validação de documento
        
        Args:
            id_doc: ID do documento
            aluno: Código do aluno
            tipo_documento: Tipo do documento
            response: Resposta da API
            valido: Se o documento é válido ('S' ou 'N')
            titular: Nome do titular do documento
        """
        query = """
        INSERT INTO DTB_ANCHIETA_PROD.DBO.ANCHI_DOCUMENTOS_ENTREGUES_VALIDA 
        (ID_DOCUMENTOS_ENTREGUES, ALUNO, TIPO_DOCUMENTO, RESPOSTA_API, VALIDO, TITULAR, DATA)
        VALUES (?, ?, ?, ?, ?, ?, GETDATE())
        """
        
        response_json = json.dumps(response, ensure_ascii=False, separators=(',', ':'))
        
        params = (
            id_doc,
            aluno,
            tipo_documento,
            response_json,
            valido,
            titular
        )
        
        return self.execute_query(query, params)
    
    def get_aluno_data(self, aluno: str) -> Optional[Dict[str, Any]]:
        """
        Obtém dados básicos do aluno
        
        Args:
            aluno: Código do aluno
            
        Returns:
            Dados do aluno ou None se não encontrado
        """
        query = """
        SELECT 
            NOME_COMPL,
            PESSOA,
            CANDIDATO
        FROM dtb_lyceum_prod.dbo.LY_ALUNO 
        WHERE ALUNO = ?
        """
        
        return self.fetch_one(query, aluno)
    
    def get_pessoa_data(self, pessoa: str) -> Optional[Dict[str, Any]]:
        """
        Obtém dados da pessoa
        
        Args:
            pessoa: Código da pessoa
            
        Returns:
            Dados da pessoa ou None se não encontrado
        """
        query = """
        SELECT 
            *
        FROM dtb_lyceum_prod.dbo.LY_PESSOA 
        WHERE PESSOA = ?
        """
        
        return self.fetch_one(query, pessoa)
    
    def get_instituicao_data(self, nome_instituicao: str) -> Optional[Dict[str, Any]]:
        """
        Obtém dados da instituição de ensino
        
        Args:
            nome_instituicao: Nome da instituição
            
        Returns:
            Dados da instituição ou None se não encontrado
        """
        query = """
        SELECT OUTRA_FACULDADE 
        FROM dtb_lyceum_prod.dbo.LY_INSTITUICAO
        WHERE NOME_COMP = ?
        """
        
        return self.fetch_one(query, nome_instituicao)
    
    def update_aluno(self, aluno: str, **kwargs) -> int:
        """
        Atualiza dados do aluno
        
        Args:
            aluno: Código do aluno
            **kwargs: Campos a serem atualizados
            
        Returns:
            Número de linhas afetadas
        """
        if not kwargs:
            return 0

        set_clauses = []
        params = []

        # Adiciona campos e valores na ordem
        for field, value in kwargs.items():
            set_clauses.append(f"{field} = ?")
            params.append(value)

        # Adiciona o valor da cláusula WHERE
        params.append(aluno)

        query = f"""
        UPDATE dtb_lyceum_prod..LY_ALUNO
        SET {', '.join(set_clauses)}
        WHERE ALUNO = ?
        """

        # Executa query passando todos os parâmetros como tupla
        return self.execute_query(query, tuple(params))
    
    def update_pessoa(self, pessoa: str, **kwargs) -> int:
        """
        Atualiza dados da pessoa
        
        Args:
            pessoa: Código da pessoa
            **kwargs: Campos a serem atualizados
            
        Returns:
            Número de linhas afetadas
        """
        if not kwargs:
            return 0
        
        set_clauses = []
        params = []
        
        for field, value in kwargs.items():
            set_clauses.append(f"{field} = ?")
            params.append(value)
        
        params.append(pessoa)

        query = f"""
        UPDATE dtb_lyceum_prod..LY_PESSOA 
        SET {', '.join(set_clauses)}
        WHERE PESSOA = ?
        """
        return self.execute_query(query, tuple(params))
    
    def update_candidato(self, candidato: str, **kwargs) -> int:
        """
        Atualiza dados do candidato
        
        Args:
            candidato: Código do candidato
            **kwargs: Campos a serem atualizados
            
        Returns:
            Número de linhas afetadas
        """
        if not kwargs:
            return 0
        
        set_clauses = []
        params = []
        
        for field, value in kwargs.items():
            set_clauses.append(f"{field} = ?")
            params.append(value)
        
        params.append(candidato)
        
        query = f"""
        UPDATE dtb_lyceum_prod..LY_CANDIDATO 
        SET {', '.join(set_clauses)}
        WHERE CANDIDATO = ?
        """
        
        return self.execute_query(query, tuple(params))

    def update_document_path(self, aluno: str, tipo_doc: str | None, url: str, coluna_antiga: str) -> None:
        """
        Atualiza o documento no banco:
        - Limpa a coluna antiga (NULL)
        - Se o tipo for reconhecido, grava na nova coluna
        - Se for OUTROS ou None, apenas mantém NULL
        """

        # Mapeamento tipo → coluna
        coluna_map = {
            'rg': 'RG',
            'cnh': 'CNH',
            'cpf': 'CPF',
            'certidao_nascimento': 'CERT_NASCIMENTO',
            'certidao_casamento': 'CERT_NASCIMENTO',
            'certidao_nascimento/casamento': 'CERT_NASCIMENTO',
            'comprovante_residencia': 'COMP_RESIDENCIA',
            'certificado_conclusao_ensino_medio': 'CERT_CONC_EN_MEDIO',
            'historico_escolar': 'HISTORICO_ESCOLAR',
            'historico_graduacao': 'HISTORICO_ESCOLAR',
            'historico_escolar_ensino_medio': 'HISTORICO_ESCOLAR',
            'carteira_vacinacao': 'CARTEIRA_VACINACAO',
            'certificado_reservista': 'CERT_RESERVISTA',
            'rg_responsavel': 'RG_RESPONSAVEL',
            'cpf_responsavel': 'CPF_RESPONSAVEL',
            'titulo_eleitor': 'TITULO_ELEITOR',
            'diploma_graduacao': 'DIPLOMA_GRADUACAO',
            'historico_fundamental': 'HISTORICO_FUNDAMENTAL',
            'declaracao_transferencia': 'DECLARACAO_TRANSFERENCIA'
        }

        coluna_antiga = coluna_map.get(coluna_antiga)
        # Passo 1 → sempre limpa a coluna antiga
        query_limpa = f"""
            UPDATE dtb_anchieta_prod.dbo.ANCHI_DOCUMENTOS_ENTREGUES
            SET {coluna_antiga} = NULL
            WHERE ALUNO = ?
        """
        self.execute_query(query_limpa, (aluno))

        # Passo 2 → verifica se tem nova coluna válida
        coluna_nova = coluna_map.get(tipo_doc)

        if not coluna_nova or tipo_doc is None or tipo_doc.upper() == "OUTROS":
            print(f"[INFO] Documento do aluno {aluno} classificado como OUTROS → não será gravado.")
            return

        # Passo 3 → grava na nova coluna
        query_update = f"""
            UPDATE dtb_anchieta_prod.dbo.ANCHI_DOCUMENTOS_ENTREGUES
            SET {coluna_nova} = ?
            WHERE ALUNO = ?
        """
        self.execute_query(query=query_update, params=(url, aluno))
    
    def get_city_code(self, cidade: str, estado: str) -> int:
        """
        Obtém dados da cidade
        
        Args:
            cidade: Cidade do documento
            estado: estado do documento
            
        Returns:
            Código da Cidade
        """
        query = """
        SELECT 
	        MUNICIPIO
        FROM dtb_lyceum_prod.dbo.HD_MUNICIPIO
            WHERE NOME = ? 
                    AND UF = ?
        """
        
        return self.fetch_one(query, (cidade, estado))