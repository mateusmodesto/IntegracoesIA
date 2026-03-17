#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerenciador de Banco de Dados - LeituraDocumentos
Operacoes especificas de validacao de documentos de alunos.
"""

import json
from typing import Dict, Any, List, Optional

from shared.database import BaseDatabaseManager


class DatabaseManager(BaseDatabaseManager):

    def delete_document_validation(self, id_doc: str, tipos_documento: List[str]) -> None:
        if not tipos_documento:
            return

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
        query = """
        SELECT
            *
        FROM dtb_lyceum_prod.dbo.LY_PESSOA
        WHERE PESSOA = ?
        """

        return self.fetch_one(query, pessoa)

    def get_instituicao_data(self, nome_instituicao: str) -> Optional[Dict[str, Any]]:
        query = """
        SELECT OUTRA_FACULDADE
        FROM dtb_lyceum_prod.dbo.LY_INSTITUICAO
        WHERE NOME_COMP = ?
        """

        return self.fetch_one(query, nome_instituicao)

    def update_aluno(self, aluno: str, **kwargs) -> int:
        if not kwargs:
            return 0

        set_clauses = []
        params = []

        for field, value in kwargs.items():
            set_clauses.append(f"{field} = ?")
            params.append(value)

        params.append(aluno)

        query = f"""
        UPDATE dtb_lyceum_prod..LY_ALUNO
        SET {', '.join(set_clauses)}
        WHERE ALUNO = ?
        """

        return self.execute_query(query, tuple(params))

    def update_pessoa(self, pessoa: str, **kwargs) -> int:
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
        query_limpa = f"""
            UPDATE dtb_anchieta_prod.dbo.ANCHI_DOCUMENTOS_ENTREGUES
            SET {coluna_antiga} = NULL
            WHERE ALUNO = ?
        """
        self.execute_query(query_limpa, (aluno))

        coluna_nova = coluna_map.get(tipo_doc)

        if not coluna_nova or tipo_doc is None or tipo_doc.upper() == "OUTROS":
            return

        query_update = f"""
            UPDATE dtb_anchieta_prod.dbo.ANCHI_DOCUMENTOS_ENTREGUES
            SET {coluna_nova} = ?
            WHERE ALUNO = ?
        """
        self.execute_query(query=query_update, params=(url, aluno))

    def get_city_code(self, cidade: str, estado: str) -> int:
        query = """
        SELECT
	        MUNICIPIO
        FROM dtb_lyceum_prod.dbo.HD_MUNICIPIO
            WHERE NOME = ?
                    AND UF = ?
        """

        return self.fetch_one(query, (cidade, estado))
