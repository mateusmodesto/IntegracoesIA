#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Classes de Migração - Sistema de Processamento de Documentos
Implementações específicas para cada tipo de documento
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

from .database_manager import DatabaseManager
from shared.utils import Utils
from shared.config import get_logger
from .api_client import ViaCEPClient

logger = get_logger(__name__)


class BaseMigration(ABC):
    """
    Classe base para migrações de documentos.
    Fornece métodos comuns para obter dados de aluno/pessoa e código de cidade.
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Inicializa a migração base

        Args:
            db_manager: Gerenciador de banco de dados
        """
        self.db = db_manager
        self.utils = Utils()

    @abstractmethod
    def migrate(self, response: Dict[str, Any], aluno: str) -> int:
        """
        Executa a migração dos dados

        Args:
            response: Dados extraídos do documento
            aluno: Código do aluno

        Returns:
            Número de linhas afetadas
        """
        pass

    def get_aluno_data(self, aluno: str) -> Optional[Dict[str, Any]]:
        """
        Obtém dados do aluno

        Args:
            aluno: Código do aluno

        Returns:
            Dados do aluno ou None
        """
        return self.db.get_aluno_data(aluno)

    def get_pessoa_data(self, pessoa: str) -> Optional[Dict[str, Any]]:
        """
        Obtém dados da pessoa

        Args:
            pessoa: Código da pessoa

        Returns:
            Dados da pessoa ou None
        """
        return self.db.get_pessoa_data(pessoa)

    def _get_city_code(self, cidade: str, estado: str) -> Optional[Dict]:
        """
        Obtém código da cidade via banco de dados

        Args:
            cidade: Nome da cidade
            estado: Sigla do estado

        Returns:
            Dicionário com dados da cidade ou None
        """
        return self.db.get_city_code(cidade, estado)


class RGMigration(BaseMigration):
    
    def migrate(self, response: Dict[str, Any], aluno: str) -> int:
        """
        Migra dados de RG
        
        Args:
            response: Dados extraídos do RG
            aluno: Código do aluno
            
        Returns:
            Número de linhas afetadas
        """
        # Extrai dados do response
        data_emissao = response['fields'].get('data_emissao', '')
        data_nascimento = response['fields'].get('data_nascimento', '')
        nome = response['fields'].get('nome_pessoa', '')
        mae = response['fields'].get('nome_mae', '')
        pai = response['fields'].get('nome_pai', '')
        rg = self.utils.clean_document_number(response['fields'].get('rg', ''))
        cpf = self.utils.format_cpf(response['fields'].get('cpf', ''))
        orgao_emissor = response['fields'].get('orgao_emissor', '')
        estado_emissor = response['fields'].get('estado_emissor', '')

        # Obtém dados do aluno
        aluno_data = self.get_aluno_data(aluno)

        if not aluno_data:
            return 0
        pessoa = aluno_data['PESSOA']
        nome_compl_atual = aluno_data['NOME_COMPL']
        
        # Escolhe o nome a usar
        nome_aluno = self.utils.choose_name(nome_compl_atual, nome)

        # Obtém dados atuais da pessoa
        pessoa_data = self.get_pessoa_data(pessoa)
        if not pessoa_data:
            return 0
         
        # Converte datas
        dt_nasc = self.utils.parse_date_br(data_nascimento)
        rg_dtexp = self.utils.parse_date_br(data_emissao)
     
        rows_affected = 0
    
        if rg and rg != pessoa_data.get('RG_NUM', ''):
            rows_affected += self.db.update_pessoa(pessoa, RG_NUM=rg)
        if orgao_emissor:
            rows_affected += self.db.update_pessoa(pessoa, RG_EMISSOR=orgao_emissor)
        if estado_emissor:
            rows_affected += self.db.update_pessoa(pessoa, RG_UF=estado_emissor)
        if cpf:
            rows_affected += self.db.update_pessoa(pessoa, CPF=cpf)
        if pai:
            rows_affected += self.db.update_pessoa(pessoa, NOME_PAI=pai.upper())
        if mae:
            rows_affected += self.db.update_pessoa(pessoa, NOME_MAE=mae.upper())
        if dt_nasc and dt_nasc != pessoa_data.get('DT_NASC'):
            rows_affected += self.db.update_pessoa(pessoa, DT_NASC=dt_nasc)
        if rg_dtexp:
            rows_affected += self.db.update_pessoa(pessoa, RG_DTEXP=rg_dtexp)
        
        if nome_aluno:
            rows_affected += self.db.update_aluno(
                aluno,
                NOME_COMPL=nome_aluno.upper(),
                NOME_ABREV=self.utils.format_name_initcap(nome_aluno)
            )
            # Atualiza dados da pessoa
            rows_affected += self.db.update_pessoa(
                pessoa,
                NOME_COMPL=nome_aluno.upper(),
                NOME_ABREV=self.utils.format_name_initcap(nome_aluno),
            )
        
        return rows_affected


class CPFMigration(BaseMigration):
    
    def migrate(self, response: Dict[str, Any], aluno: str) -> int:
        """
        Migra dados de CPF
        
        Args:
            response: Dados extraídos do CPF
            aluno: Código do aluno
            
        Returns:
            Número de linhas afetadas
        """
        # Extrai dados do response
        numero_documento = self.utils.clean_document_number(response['fields'].get('cpf', ''))
        data_nascimento = response['fields'].get('data_nascimento', '')
        nome = response['fields'].get('nome_pessoa', '')
        
        # Obtém dados do aluno
        aluno_data = self.get_aluno_data(aluno)
        if not aluno_data:
            return 0
        
        pessoa = aluno_data['PESSOA']
        nome_compl_atual = aluno_data['NOME_COMPL']
        
        # Escolhe o nome a usar
        nome_aluno = self.utils.choose_name(nome_compl_atual, nome)
        
        # Obtém dados atuais da pessoa
        pessoa_data = self.get_pessoa_data(pessoa)
        if not pessoa_data:
            return 0
        
        cpf_atual = pessoa_data.get('CPF', '')
        dt_nasc_atual = pessoa_data.get('DT_NASC')
        
        # Converte data de nascimento
        dt_nasc = self.utils.parse_date_br(data_nascimento)
        
        rows_affected = 0
        
        # Atualiza data de nascimento se válida e diferente
        if dt_nasc and dt_nasc != dt_nasc_atual:
            rows_affected += self.db.update_pessoa(pessoa, DT_NASC=dt_nasc)
        
        # Atualiza CPF se diferente
        if numero_documento and numero_documento != cpf_atual:
            rows_affected += self.db.update_pessoa(pessoa, CPF=numero_documento)
        
        # Atualiza dados do aluno
        if nome_aluno:
            rows_affected += self.db.update_aluno(
                aluno,
                NOME_COMPL=nome_aluno.upper(),
                NOME_ABREV=self.utils.format_name_initcap(nome_aluno)
            )
        
            # Atualiza dados da pessoa
            rows_affected += self.db.update_pessoa(
                pessoa,
                NOME_COMPL=nome_aluno.upper(),
                NOME_ABREV=self.utils.format_name_initcap(nome_aluno)
            )
        
        return rows_affected

class CertidaoNascimentoMigration(BaseMigration):
    
    def migrate(self, response: Dict[str, Any], aluno: str) -> int:
        """
        Migra dados de Certidão de Nascimento
        
        Args:
            response: Dados extraídos da certidão
            aluno: Código do aluno
            
        Returns:
            Número de linhas afetadas
        """
        # Extrai dados do response
        nome_pai = response['fields'].get('nome_pai', '')
        nome_mae = response['fields'].get('nome_mae', '')
        cidade_nascimento = response['fields'].get('cidade_nascimento', '')
        estado_nascimento = response['fields'].get('estado_nascimento', '')
        
        # Busca código da cidade (implementação simplificada)
        codcidade = self._get_city_code(cidade_nascimento, estado_nascimento)
       
        # Obtém dados do aluno
        aluno_data = self.get_aluno_data(aluno)
        
        if not aluno_data:
            return 0
        
        pessoa = aluno_data['PESSOA']
        
        rows_affected = 0
        
        # Atualiza dados da pessoa
        if nome_pai:
            rows_affected += self.db.update_pessoa(
                pessoa,
                NOME_PAI=nome_pai.upper() if nome_pai else None
            )
        if nome_mae:
            rows_affected += self.db.update_pessoa(
                pessoa,
                NOME_MAE=nome_mae.upper() if nome_mae else None
            )
        if codcidade and codcidade.get('MUNICIPIO'):
            rows_affected += self.db.update_pessoa(
                pessoa,
                MUNICIPIO_NASC=codcidade['MUNICIPIO']
            )

        return rows_affected


class CertidaoCasamentoMigration(BaseMigration):
    
    def migrate(self, response: Dict[str, Any], aluno: str) -> int:
        """
        Migra dados de Certidão de Casamento
        
        Args:
            response: Dados extraídos da certidão
            aluno: Código do aluno
            
        Returns:
            Número de linhas afetadas
        """
        # Extrai dados do response
        nome_noivo = response['fields'].get('nome_noivo_pos_casamento', '')
        nome_noiva = response['fields'].get('nome_noiva_pos_casamento', '')
        
        # Obtém dados do aluno
        aluno_data = self.get_aluno_data(aluno)
        if not aluno_data:
            return 0
        
        pessoa = aluno_data['PESSOA']
        nome_aluno = aluno_data['NOME_COMPL']
        
        rows_affected = 0
        
        # Determina se o aluno é noivo ou noiva
        if nome_aluno in nome_noivo:
            # Aluno é noivo
            nome_conjuge = nome_noiva

        elif nome_aluno in nome_noiva:
            # Aluno é noiva
            nome_conjuge = nome_noivo
        else:
            nome_conjuge = None
          
        
        # Atualiza dados da pessoa
        if nome_conjuge:
            rows_affected += self.db.update_pessoa(
                pessoa,
                NOME_CONJUGE=nome_conjuge.upper() if nome_conjuge else None,
                EST_CIVIL='Casado'
            )
        
        return rows_affected

class ComprovanteResidenciaMigration(BaseMigration):
    
    def migrate(self, response: Dict[str, Any], aluno: str) -> int:
        """
        Migra dados de Comprovante de Residência
        
        Args:
            response: Dados extraídos do comprovante
            aluno: Código do aluno
            
        Returns:
            Número de linhas afetadas
        """
        # Extrai dados do response
        cep = self.utils.clean_document_number(response['fields'].get('cep', ''))
        endereco = response['fields'].get('endereco', '')
        
        if not cep:
            raise Exception("CEP não informado")
        
        # Extrai número do endereço
        numero = self.utils.extract_address_number(endereco)
        
        # Consulta CEP via API
        try:
            with ViaCEPClient() as viacep:
                dados_cep = viacep.consultar_cep(cep)
        except Exception as e:
            raise Exception(f"Erro ao consultar CEP: {str(e)}")
        
        logradouro = dados_cep.get('logradouro', '')
        bairro = dados_cep.get('bairro', '')
        cidade = dados_cep.get('localidade', '')
        uf = dados_cep.get('uf', '')
        
        # Busca código da cidade
        codcidade = self._get_city_code(cidade, uf)
        
        # Obtém dados do aluno
        aluno_data = self.get_aluno_data(aluno)
        if not aluno_data:
            return 0
        
        pessoa = aluno_data['PESSOA']
        
        rows_affected = 0
        
        # Atualiza dados de endereço da pessoa
        if cep and logradouro:
            
            rows_affected += self.db.update_pessoa(
                pessoa,
                CEP=cep,
                ENDERECO=logradouro,
                END_NUM=numero if numero else None,
                END_MUNICIPIO=codcidade['MUNICIPIO'] if codcidade and codcidade.get('MUNICIPIO') else None,
                BAIRRO=bairro if bairro else None
            )
        
        return rows_affected


class CertificadoMedioMigration(BaseMigration):
    
    def migrate(self, response: Dict[str, Any], aluno: str) -> int:
        """
        Migra dados de Certificado de Conclusão do Ensino Médio
        
        Args:
            response: Dados extraídos do certificado
            aluno: Código do aluno
            
        Returns:
            Número de linhas afetadas
        """
        # Extrai dados do response
        ano_conclusao = response['fields']['conclusao'].get('ano_conclusao', '')
        instituicao_ensino = response['fields']['conclusao'].get('instituicao_ensino', '')
        
        # Obtém dados do aluno
        aluno_data = self.get_aluno_data(aluno)
        if not aluno_data:
            return 0
        
        candidato = aluno_data.get('CANDIDATO')
        
        # Busca dados da instituição
        instituicao_data = self.db.get_instituicao_data(instituicao_ensino)
        instituicao = instituicao_data.get('OUTRA_FACULDADE') if instituicao_data else None
        
        rows_affected = 0
        
        # Atualiza instituição se encontrada
        if instituicao:
            if candidato:
                rows_affected += self.db.update_candidato(
                    candidato,
                    INSTITUICAO_ANTERIOR=instituicao,
                    OUTRA_FACULDADE=instituicao
                )
            
            rows_affected += self.db.update_aluno(
                aluno,
                OUTRA_FACULDADE=instituicao
            )
        
        # Atualiza ano de conclusão se válido
        if ano_conclusao:
            rows_affected += self.db.update_aluno(
                aluno,
                ANOCONCL_2G=ano_conclusao
            )
            
            if candidato:
                rows_affected += self.db.update_candidato(
                    candidato,
                    ANOCONCL_2G=ano_conclusao
                )
        
        return rows_affected

class CertificadoGraduacaoMigration(BaseMigration):
    
    def migrate(self, response: Dict[str, Any], aluno: str) -> int:
        """
        Migra dados de Certificado de Conclusão da Graduacao
        
        Args:
            response: Dados extraídos do certificado
            aluno: Código do aluno
            
        Returns:
            Número de linhas afetadas
        """
        # Extrai dados do response
        instituicao_ensino = response['fields']['conclusao'].get('instituicao_ensino', '')
        
        # Obtém dados do aluno
        aluno_data = self.get_aluno_data(aluno)
        if not aluno_data:
            return 0
        
        candidato = aluno_data.get('CANDIDATO')
        
        # Busca dados da instituição
        instituicao_data = self.db.get_instituicao_data(instituicao_ensino)
        instituicao = instituicao_data.get('OUTRA_FACULDADE') if instituicao_data else None
        
        rows_affected = 0
        
        # Atualiza instituição se encontrada
        if instituicao:
            if candidato:
                rows_affected += self.db.update_candidato(
                    candidato,
                    INSTITUICAO_ANTERIOR=instituicao,
                    OUTRA_FACULDADE=instituicao
                )
            
            rows_affected += self.db.update_aluno(
                aluno,
                OUTRA_FACULDADE=instituicao
            )
        
        return rows_affected

class HistoricoEscolarMigration(BaseMigration):
    
    def migrate(self, response: Dict[str, Any], aluno: str) -> int:
        """
        Migra dados de Histórico Escolar
        
        Args:
            response: Dados extraídos do histórico
            aluno: Código do aluno
            
        Returns:
            Número de linhas afetadas
        """
        # Extrai dados do response
        instituicao_ensino = response['fields']['historico'].get('instituicao_ensino', '')
        
        # Obtém dados do aluno
        aluno_data = self.get_aluno_data(aluno)
        if not aluno_data:
            return 0
        
        candidato = aluno_data.get('CANDIDATO')
        
        # Busca dados da instituição
        instituicao_data = self.db.get_instituicao_data(instituicao_ensino)
        instituicao = instituicao_data.get('OUTRA_FACULDADE') if instituicao_data else None
        
        rows_affected = 0
        
        # Atualiza instituição se encontrada
        if instituicao:
            if candidato:
                rows_affected += self.db.update_candidato(
                    candidato,
                    INSTITUICAO_ANTERIOR=instituicao,
                    OUTRA_FACULDADE=instituicao
                )
            
            rows_affected += self.db.update_aluno(
                aluno,
                OUTRA_FACULDADE=instituicao
            )
        
        
        return rows_affected
    
class CarteiraVacinacaoMigration(BaseMigration):
    
    def migrate(self, response: Dict[str, Any], aluno: str) -> int:
        """
        Migra dados de Carteira de Vacinação
        
        Args:
            response: Dados extraídos da carteira de vacinação
            aluno: Código do aluno
            
        Returns:
            Número de linhas afetadas
        """
        # Extrai dados do response
        nome = response.get('nome', '')
        data_nascimento = response.get('data_nascimento', '')
        cpf = self.utils.clean_document_number(response.get('cpf', ''))
        nome_mae = response.get('mae', '')
        nome_pai = response.get('pai', '')
        numero_carteira = response.get('numero_carteira', '')
        data_emissao = response.get('data_emissao', '')
        orgao_emissor = response.get('orgao_emissor', '')
        
        # Obtém dados do aluno
        aluno_data = self.get_aluno_data(aluno)
        if not aluno_data:
            return 0
        
        pessoa = aluno_data['PESSOA']
        nome_compl_atual = aluno_data['NOME_COMPL']
        
        # Escolhe o nome a usar
        nome_aluno = self.utils.choose_name(nome_compl_atual, nome)
        
        # Obtém dados atuais da pessoa
        pessoa_data = self.get_pessoa_data(pessoa)
        if not pessoa_data:
            return 0
        
        cpf_atual = pessoa_data.get('CPF', '')
        dt_nasc_atual = pessoa_data.get('DT_NASC')
        
        # Converte data de nascimento
        dt_nasc = self.utils.parse_date_br(data_nascimento)
        
        rows_affected = 0
        
        # Atualiza data de nascimento se válida e diferente
        if dt_nasc and dt_nasc != dt_nasc_atual:
            rows_affected += self.db.update_pessoa(pessoa, DT_NASC=dt_nasc)
        
        # Atualiza CPF se diferente
        if cpf and cpf != cpf_atual:
            rows_affected += self.db.update_pessoa(pessoa, CPF=cpf)
        
        # Atualiza nomes dos pais
        rows_affected += self.db.update_pessoa(
            pessoa,
            NOME_PAI=nome_pai.upper() if nome_pai else None,
            NOME_MAE=nome_mae.upper() if nome_mae else None
        )
        
        return rows_affected

class CertificadoReservistaMigration(BaseMigration):
    
    def migrate(self, response: Dict[str, Any], aluno: str) -> int:
        """
        Migra dados de Certificado de Reservista
        
        Args:
            response: Dados extraídos do certificado
            aluno: Código do aluno
            
        Returns:
            Número de linhas afetadas
        """
        # Extrai dados do response
        numero_alistamento = response['fields'].get('ra', '')
        serie_alistamento = response['fields'].get('serie', '')
        rm_alistamento = response['fields'].get('rm', '') 
        
        # Obtém dados do aluno
        aluno_data = self.get_aluno_data(aluno)
        if not aluno_data:
            return 0
        
        pessoa = aluno_data['PESSOA']
        
        # Escolhe o nome a usar
        
        # Obtém dados atuais da pessoa
        pessoa_data = self.get_pessoa_data(pessoa)
        if not pessoa_data:
            return 0
        rows_affected = 0
    
        # Atualiza dados do alistamento militar
        if numero_alistamento:
            rows_affected += self.db.update_pessoa(
                pessoa,
                ALIST_NUM=numero_alistamento
            )
        if serie_alistamento:
            rows_affected += self.db.update_pessoa(
                pessoa,
                ALIST_SERIE=serie_alistamento 
            )
        if rm_alistamento:
            rows_affected += self.db.update_pessoa(
                pessoa,
                ALIST_RM=rm_alistamento
            )
        
        return rows_affected

class DocumentosResponsavelMigration(BaseMigration):
    """
    Migração de dados de Documentos do Responsável (RG e CPF)
    """
    
    def migrate(self, response: Dict[str, Any], aluno: str) -> int:
        """
        Migra dados de Documentos do Responsável
        
        Args:
            response: Dados extraídos do documento
            aluno: Código do aluno
            
        Returns:
            Número de linhas afetadas
        """
        # Extrai dados do response
        if response.get('document_type') == 'rg' or response.get('document_type') == 'cnh':
            data_emissao = response['fields'].get('data_emissao', '')
            data_nascimento = response['fields'].get('data_nascimento', '')
            nome = response['fields'].get('nome_pessoa', '')
            mae = response['fields'].get('nome_mae', '')
            pai = response['fields'].get('nome_pai', '')
            rg = self.utils.clean_document_number(response['fields'].get('rg', ''))
            orgao_emissor = response['fields'].get('orgao_emissor', '')
            cpf = self.utils.clean_document_number(response['fields'].get('cpf', ''))
            
            resultado = self.db.fetch_one(
                "SELECT PESSOA, NOME_COMPL FROM LY_PESSOA A where NOME_COMPL LIKE ?",
                (nome)
            )
            if not resultado:
                return 0

            pessoa = resultado['PESSOA']
            nome_compl_atual = resultado['NOME_COMPL']
             
            
            # Escolhe o nome a usar
            nome = self.utils.choose_name(nome_compl_atual, nome)

            
            # Converte datas
            dt_nasc = self.utils.parse_date_br(data_nascimento)
            rg_dtexp = self.utils.parse_date_br(data_emissao)
        
            rows_affected = 0
            
            if rg and rg != pessoa:
                rows_affected += self.db.update_pessoa(pessoa, RG_NUM=rg)
            if orgao_emissor:
                rows_affected += self.db.update_pessoa(pessoa, RG_EMISSOR=orgao_emissor)
            if cpf:
                rows_affected += self.db.update_pessoa(pessoa, CPF=cpf)
            if pai:
                rows_affected += self.db.update_pessoa(pessoa, NOME_PAI=pai.upper())
            if mae:
                rows_affected += self.db.update_pessoa(pessoa, NOME_MAE=mae.upper())
            if dt_nasc:
                rows_affected += self.db.update_pessoa(pessoa, DT_NASC=dt_nasc)
            if rg_dtexp:
                rows_affected += self.db.update_pessoa(pessoa, RG_DTEXP=rg_dtexp)
            
            if nome:
                rows_affected += self.db.update_pessoa(
                    pessoa,
                    NOME_COMPL=nome.upper(),
                    NOME_ABREV=self.utils.format_name_initcap(nome),
                )
            
               
            return rows_affected
        
        else:
            numero_documento = self.utils.clean_document_number(response['fields'].get('cpf', ''))
            data_nascimento = response['fields'].get('data_nascimento', '')
            nome = response['fields'].get('nome_pessoa', '')
            
            # Obtém dados do aluno
            resultado = self.db.fetch_one(
                "SELECT PESSOA, NOME_COMPL FROM LY_PESSOA A where NOME_COMPL LIKE ?",
                (nome)
            )
            if not resultado:
                return 0
            pessoa = resultado['PESSOA']
            nome_compl_atual = resultado['NOME_COMPL']
             
            
            # Escolhe o nome a usar
            nome = self.utils.choose_name(nome_compl_atual, nome)
            
            # Converte data de nascimento
            dt_nasc = self.utils.parse_date_br(data_nascimento)
            
            rows_affected = 0
            
            # Atualiza data de nascimento se válida
            if dt_nasc:
                rows_affected += self.db.update_pessoa(pessoa, DT_NASC=dt_nasc)
            
            # Atualiza CPF se diferente
            if numero_documento :
                rows_affected += self.db.update_pessoa(pessoa, CPF=numero_documento)
            
            # Atualiza dados do aluno
            if nome:
                # Atualiza dados da pessoa
                rows_affected += self.db.update_pessoa(
                    pessoa,
                    NOME_COMPL=nome.upper(),
                    NOME_ABREV=self.utils.format_name_initcap(nome)
                )
            
            return rows_affected

class TituloEleitorMigration(BaseMigration):
    
    def migrate(self, response: Dict[str, Any], aluno: str) -> int:
        """
        Migra dados de Título de Eleitor
        
        Args:
            response: Dados extraídos do título
            aluno: Código do aluno
            
        Returns:
            Número de linhas afetadas
        """
        # Extrai dados do response
        nome = response['fields'].get('nome_pessoa', '')
        data_nascimento = response['fields'].get('data_nascimento', '')
        numero_titulo = response['fields'].get('numero_titulo', '')
        zona = response['fields'].get('zona', '')
        secao = response['fields'].get('secao', '')
        data_expedicao = response['fields'].get('data_emissao', '')
        municipio = self._get_city_code(response['fields'].get('municipio', ''), response['fields'].get('estado', ''))
        
        # Obtém dados do aluno
        aluno_data = self.get_aluno_data(aluno)
        if not aluno_data:
            return 0
        
        pessoa = aluno_data['PESSOA']
        nome_compl_atual = aluno_data['NOME_COMPL']
        
        # Escolhe o nome a usar
        nome_aluno = self.utils.choose_name(nome_compl_atual, nome)
        
        # Obtém dados atuais da pessoa
        pessoa_data = self.get_pessoa_data(pessoa)
        if not pessoa_data:
            return 0
        
        dt_nasc_atual = pessoa_data.get('DT_NASC')
        
        # Converte datas
        dt_nasc = self.utils.parse_date_br(data_nascimento)
        dt_expedicao = self.utils.parse_date_br(data_expedicao)
        
        rows_affected = 0

        # Atualiza data de nascimento se válida e diferente
        if dt_nasc and dt_nasc != dt_nasc_atual:
            rows_affected += self.db.update_pessoa(pessoa, DT_NASC=dt_nasc)
        
        # Atualiza dados do título de eleitor
        if numero_titulo:
            rows_affected += self.db.update_pessoa(
                pessoa,
                TELEITOR_NUM=numero_titulo
            )
        if zona:
            rows_affected += self.db.update_pessoa(
                pessoa,
                TELEITOR_ZONA=zona
            )
        if secao:
            rows_affected += self.db.update_pessoa(
                pessoa,
                TELEITOR_SECAO=secao 
            )
        if dt_expedicao:
            rows_affected += self.db.update_pessoa(
                pessoa,
                TELEITOR_DTEXP=dt_expedicao
            )
        if municipio and municipio.get('MUNICIPIO'):
            rows_affected += self.db.update_pessoa(
                pessoa,
                TELEITOR_MUN=municipio['MUNICIPIO']
            )
        if nome_aluno:
            rows_affected += self.db.update_aluno(
                aluno,
                NOME_COMPL=nome_aluno.upper(),
                NOME_ABREV=self.utils.format_name_initcap(nome_aluno)
            )
            
            # Atualiza dados da pessoa
            rows_affected += self.db.update_pessoa(
                pessoa,
                NOME_COMPL=nome_aluno.upper(),
                NOME_ABREV=self.utils.format_name_initcap(nome_aluno)
            )
        return rows_affected


class HistoricoFundamentalMigration(BaseMigration):
    
    def migrate(self, response: Dict[str, Any], aluno: str) -> int:
        """
        Migra dados de Histórico Escolar do Ensino Fundamental
        
        Args:
            response: Dados extraídos do histórico
            aluno: Código do aluno
            
        Returns:
            Número de linhas afetadas
        """
        # Extrai dados do response
        instituicao_ensino = response['fields']['conclusao'].get('instituicao_ensino', '')
        
        # Obtém dados do aluno
        aluno_data = self.get_aluno_data(aluno)
        if not aluno_data:
            return 0
        
        candidato = aluno_data.get('CANDIDATO')
        
        # Busca dados da instituição
        instituicao_data = self.db.get_instituicao_data(instituicao_ensino)
        instituicao = instituicao_data.get('OUTRA_FACULDADE') if instituicao_data else None
        
        rows_affected = 0
        
        # Atualiza instituição se encontrada
        if instituicao:
            if candidato:
                rows_affected += self.db.update_candidato(
                    candidato,
                    INSTITUICAO_ANTERIOR=instituicao,
                    OUTRA_FACULDADE=instituicao
                )
            
            rows_affected += self.db.update_aluno(
                aluno,
                OUTRA_FACULDADE=instituicao
            )
        
        return rows_affected

class DeclaracaoTransferenciaMigration(BaseMigration):
    
    def migrate(self, response: Dict[str, Any], aluno: str) -> int:
        """
        Migra dados de Declaração de Transferência
        
        Args:
            response: Dados extraídos da declaração
            aluno: Código do aluno
            
        Returns:
            Número de linhas afetadas
        """
        instituicao_ensino = response['fields'].get('instituicao_origem', '')
        
        # Obtém dados do aluno
        aluno_data = self.get_aluno_data(aluno)
        if not aluno_data:
            return 0
        
        candidato = aluno_data.get('CANDIDATO')
        
        # Busca dados da instituição
        instituicao_data = self.db.get_instituicao_data(instituicao_ensino)
        instituicao = instituicao_data.get('OUTRA_FACULDADE') if instituicao_data else None
        
        rows_affected = 0
        
        # Atualiza instituição se encontrada
        if instituicao:
            if candidato:
                rows_affected += self.db.update_candidato(
                    candidato,
                    INSTITUICAO_ANTERIOR=instituicao,
                    OUTRA_FACULDADE=instituicao
                )
            
            rows_affected += self.db.update_aluno(
                aluno,
                OUTRA_FACULDADE=instituicao
            )
        
        return rows_affected
