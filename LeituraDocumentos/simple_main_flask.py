#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema Simplificado de Processamento de Documentos
Método main que busca documentos no banco, processa via API e atualiza dados
"""

import json
from typing import Dict, Any, List
from datetime import datetime
import time
from .LerDocumentoClass import Gemini
from .database_manager import DatabaseManager
from .migration_classes import (
    RGMigration,
    CPFMigration,
    CertidaoNascimentoMigration,
    CertidaoCasamentoMigration,
    ComprovanteResidenciaMigration,
    CertificadoMedioMigration,
    CertificadoGraduacaoMigration,
    HistoricoEscolarMigration,
    CarteiraVacinacaoMigration,
    CertificadoReservistaMigration,
    DocumentosResponsavelMigration,
    TituloEleitorMigration,
    HistoricoFundamentalMigration,
    DeclaracaoTransferenciaMigration
)



class SimpleDocumentProcessor:
    """
    Processador simplificado de documentos
    """
    def __init__(self, database_config: Dict[str, Any]):
        """
        Inicializa o processador
        
        Args:
            database_config: Configurações do banco de dados
        """
        self.db_manager = DatabaseManager(database_config)
        self.gemi = Gemini()
        # Configura o API client com timeout maior e retry para lidar com timeouts
        # self.api_client = APIClient(timeout=60, max_retries=3, retry_delay=10)
        
        # Mapeamento de tipos de documento para classes de migração
        self.migration_classes = {
            'rg': RGMigration,
            #'cnh': CNHMigration,
            'cpf': CPFMigration,
            'rg_aluno': RGMigration,
            'cpf_aluno': CPFMigration,
            'certidao_nascimento': CertidaoNascimentoMigration,
            'certidao_casamento': CertidaoCasamentoMigration,
            'comprovante_residencia': ComprovanteResidenciaMigration,
            'certificado_conclusao_ensino_medio': CertificadoMedioMigration,
            'certificado_diploma_graduacao': CertificadoGraduacaoMigration,
            'historico_escolar': HistoricoEscolarMigration,
            'historico_escolar_fundamental': HistoricoFundamentalMigration,
            'carteira_vacinação': CarteiraVacinacaoMigration,
            'certificado_reservista': CertificadoReservistaMigration,
            'rg_responsavel': DocumentosResponsavelMigration,
            'cpf_responsavel': DocumentosResponsavelMigration,
            'titulo_eleitor': TituloEleitorMigration,
            'declaracao_transferencia': DeclaracaoTransferenciaMigration
        }
        self.MAPA_DOCUMENTOS = {
            "escola": {
                'certidao_nascimento/casamento': "CERT_NASCIMENTO",
                'rg': "RG",
                'cpf': "CPF",
                'historico_transf': "HISTORICO_ESCOLAR",
                'declaracao_transf': "DECL_TRANSFERENCIA",
                'comprovante_residencia': "COMP_RESIDENCIA",
                'rg_responsavel': "RG_RESPONSAVEL",
                'cpf_responsavel': "CPF_RESPONSAVEL",
                'historico_escolar_fundamental': "HISTORICO_FUNDAMENTAL",
                'cartao_vacina': "CARTEIRA_VACINA"
            },
            "graduacao": {
                'certidao_nascimento/casamento': "CERT_NASCIMENTO",
                'certificado_conclusao_ensino_medio': "CERT_CONC_EN_MEDIO",
                'cert_reservista': "CERT_RESERVISTA",
                'comprovante_residencia': "COMP_RESIDENCIA",
                'cpf': "CPF",
                'historico_escolar': "HISTORICO_ESCOLAR",
                'rg': "RG",
                'titulo_eleitor': "TITULO_ELEITOR"
            },
            "pos_graduacao": {
                'certidao_nascimento/casamento': "CERT_NASCIMENTO",
                'comprovante_residencia': "COMP_RESIDENCIA",
                'cpf': "CPF",
                'certificado_diploma_graduacao': "DIPLOMA_GRADUACAO",
                'historico_escolar': "HISTORICO_ESCOLAR",
                'rg': "RG"
            }
        }


    def process_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa um documento individual
        
        Args:
            document: Dados do documento
            
        Returns:
            Resultado do processamento
        """
        # Extrai dados do documento
        try:
            aluno = document['ALUNO']
            url_doc = document['CAMINHO']
            usuario = document['ALUNO']
            posicao = document['POSICAO']
            curso_entrega = document['ENSINO']

            base = "https://ged-anchieta.s3.amazonaws.com/"
            
            tipo_doc =  posicao
            
        except Exception as e:
            return {
                "status": "error",
                'message': f'Erro ao extrair dados do documento: {str(e)}'
            }
        try:
            api_resposta = self.gemi.analisarDocumento(url=url_doc, origem=curso_entrega, tipo_doc=tipo_doc)
            if api_resposta.get('Erro'):
                return {
                    "status": "error",
                    'message': 'Erro ao se conectar com a IA',
                    'api_resposta': api_resposta
                }

            validacao = api_resposta.get('validacao', {})
            extracao = api_resposta.get('extracao', {})

            # Verifica se a API retornou dados válidos
            if validacao.get('is_valid') == True and extracao:
                if tipo_doc == 'certidao_nascimento/casamento':
                    match validacao['document_type']:
                        case 'certidao_nascimento':
                            is_valid = self._determine_document_validity(extracao, 'certidao_nascimento')
                            titular = extracao['fields'].get('nome_pessoa')
                            tipo_extra = 'certidao_nascimento'
                        case 'certidao_casamento':
                            is_valid = self._determine_document_validity(extracao, 'certidao_casamento')
                            titular = None
                            tipo_extra = 'certidao_casamento'
                        case _:
                            is_valid = False
                            titular = None
                            tipo_extra = None

                else:
                    is_valid = self._determine_document_validity(extracao, tipo_doc)

                    titular = extracao['fields'].get('nome_pessoa')
                    tipo_extra = None

                if is_valid == True:

                    resposta = self.insert_document_delivery(
                        aluno=aluno,
                        url_doc=url_doc,
                        curso_entrega=curso_entrega,
                        posicao=posicao,
                        usuario=usuario,
                        tipo_doc=tipo_doc,
                        api_resposta=extracao,
                        is_valid=is_valid,
                        titular=titular,
                        base=base,
                        tipo_extra=tipo_extra
                    )

                    if resposta['status'] == True:
                        return {'status': "sucesso", "Documento": resposta}
                    else:
                        return {'status': "error", "Documento": resposta}
                else:
                    return {'status': "error", 'message': 'Documento considerado inválido pela validação interna'}
            else:
                return {
                    "status": "error",
                    'message': 'Resposta vazia da API ou documento inválido',
                    'api_resposta': api_resposta
                }

        except Exception as e:
            # Verifica se é um erro de timeout ou 504
            is_timeout_error = (
                'timeout' in str(e).lower() or
                '504' in str(e) or
                'endpoint request timed out' in str(e).lower()
            )

            if is_timeout_error:
                return {
                    'status': 'error',
                    'status': 'timeout',
                    'retry_needed': True
                }

            return {
                "status": "error",
                'message': str(e),
                'api_resposta': api_resposta,
                'retry_needed': False
            }
    
    
    def _determine_document_validity(self, data: Dict[str, Any], tipo_doc: str) -> bool:
        """
        Determina se um documento é válido baseado nos dados extraídos
        
        Args:
            data: Dados extraídos do documento
            tipo_doc: Tipo do documento
            
        Returns:
            True se o documento é válido, False caso contrário
        """
        # Validações básicas por tipo de documento
       
        if tipo_doc == 'rg' or tipo_doc == 'rg_responsavel':
            # Para documentos de identificação, verifica se tem nome e número
            if data.get('is_valid') == False or data.get('is_valid') is None and data['document_type'] not in ('rg', 'cnh'):
                return False
            else:
                return bool(data['fields'].get('rg') and data['fields'].get('nome_pessoa')) 
                            
        elif tipo_doc == 'cpf' or tipo_doc == 'cpf_responsavel':
            # Para documentos de identificação, verifica se tem nome e número
            if data.get('is_valid') == False or data.get('is_valid') is None and data['document_type'] not in ('rg', 'cnh', 'cpf'):
                return False
            else:
                return bool(data['fields'].get('cpf') and data['fields'].get('nome_pessoa'))           
                
        elif tipo_doc == 'cnh':
            # Para documentos de identificação, verifica se tem nome e número
            if data.get('is_valid') == False or data.get('is_valid') is None and data['document_type'] not in ('rg', 'cnh'):
                return False
            else:
                return bool(data['fields'].get('cpf') and data['fields'].get('nome_pessoa') and data['fields'].get('rg') and data['fields'].get('data_nascimento') and data['fields'].get('nome_pai') and data['fields'].get('nome_mae'))
                
        elif tipo_doc in ['certidao_nascimento']:
            # Para certidões, verifica se tem nome
            if data.get('is_valid') == False or data.get('is_valid') is None and data['document_type'] not in ('certidao_nascimento'):
                return False
            else:
                return bool(data['fields'].get('nome_pessoa') and data['fields'].get('data_nascimento') and data['fields'].get('local_nascimento'))
        
        elif tipo_doc in ['certidao_casamento']:
            if data.get('is_valid') == False or data.get('is_valid') is None and data['document_type'] not in ('certidao_casamento'):
                return False
            else:
                return bool(data['fields'].get('nome_noivo_pos_casamento') and data['fields'].get('data_casamento') and data['fields'].get('nome_noiva_pos_casamento'))
        
        elif tipo_doc == 'comprovante_residencia':
            # Para comprovante, verifica se tem CEP e endereço
            if data.get('is_valid') == False or data.get('is_valid') is None and data['document_type'] not in ('comprovante_residencia'):
                return False
            else:
                return bool(data['fields'].get('cep') and data['fields'].get('endereco'))
        
        elif tipo_doc in ['certificado_conclusao_ensino_medio']:
            
            if (data.get('is_valid') == False or data.get('is_valid') is None)  and data['document_type'] not in ('conclusao_historico'):
                return False
            else:
                if data.get('origem_entrega') == 'graduacao' and data['fields'].get('conclusao', '') != '':
                    return bool(data['fields']['conclusao'].get('instituicao_ensino') and data['fields'].get('nome_pessoa') and data['fields']['conclusao'].get('ano_conclusao'))
                else:
                    return False
                
        elif tipo_doc in ['certificado_diploma_graduacao']:
            
            if (data.get('is_valid') == False or data.get('is_valid') is None) and data['document_type'] not in ('conclusao_historico'):
                return False
            else:
                if data.get('origem_entrega') == 'pos_graduacao'  and data['fields'].get('conclusao', '') != '':
                    return bool(data['fields']['conclusao'].get('instituicao_ensino') and data['fields'].get('nome_pessoa') and data['fields']['conclusao'].get('ano_conclusao'))
                else:
                    return False
                
        elif tipo_doc in ['historico_escolar_fundamental']:
            if (data.get('is_valid') == False or data.get('is_valid') is None) and data['document_type'] not in ('conclusao_historico'):
                return False
            else:
                if data.get('origem_entrega') == 'escola' and data['fields'].get('conclusao', '') != '' :
                    return bool(data['fields']['historico'].get('instituicao_ensino') and data['fields'].get('nome_pessoa'))
                else:
                    return False
                
        elif tipo_doc in ['historico_escolar']:           
            if (data.get('is_valid') == False or data.get('is_valid') is None) and data['fields'].get('historico', '') == '' and data['document_type'] not in ('conclusao_historico'):
                return False
            else:
                if data.get('origem_entrega') == 'graduacao' or data.get('origem_entrega') == 'pos_graduacao':
                    return bool(data['fields']['historico'].get('instituicao_ensino') and data['fields'].get('nome_pessoa'))
                else:
                    return False
                
        elif tipo_doc in ['declaracao_transferencia']:
            if (data.get('is_valid') == False or data.get('is_valid') is None) and data.get('origem_entrega') != 'escola' and data['document_type'] not in ('declaracao_transferencia'):
                return False
            else:
                return bool(data['fields'].get('nome_pessoa') and data['fields'].get('instituicao_origem') and data['fields'].get('data_emissao'))
            
        elif tipo_doc == 'carteira_vacinacao':  
            # Para carteira de vacinação, verifica se tem nome e número da carteira
            if data.get('is_valid') == False or data.get('is_valid') is None:
                return False
            else:
                return True
        
        elif tipo_doc == 'certificado_reservista':
            # Para certificado reservista, verifica se tem nome e número de alistamento
            if data.get('is_valid') == False or data.get('is_valid') is None and data['document_type'] not in ('certificado_reservista'):
                return False
            else:
                return bool(data['fields'].get('nome_pessoa') and data['fields'].get('ra') and data['fields'].get('cpf'))
        
        elif tipo_doc == 'titulo_eleitor':
            # Para título de eleitor, verifica se tem nome e número do título
            if data.get('is_valid') == False or data.get('is_valid') is None and data['document_type'] not in ('titulo_eleitor'):
                return False
            else:
                return bool(data['fields'].get('nome_pessoa') and data['fields'].get('data_nascimento') and data['fields'].get('municipio')
                            and data['fields'].get('estado') and data['fields'].get('zona') and data['fields'].get('secao') 
                            and data['fields'].get('data_emissao') and data['fields'].get('numero_titulo')
                        )

    def insert_document_delivery(self, aluno, url_doc, curso_entrega, posicao, usuario, tipo_doc, api_resposta, is_valid, titular, base, tipo_extra=None):
        coluna = self.MAPA_DOCUMENTOS.get(curso_entrega, {}).get(posicao)
        if not coluna:
            return {"status": False, "Mensagem": "Curso ou posição inválida"}
        
        # Atualiza documento do aluno
        query_update = f"""
            UPDATE DTB_ANCHIETA_PROD.DBO.ANCHI_DOCUMENTOS_ENTREGUES
            SET {coluna} = ?
            WHERE ALUNO = ?
            AND ATIVO = '1'
        """
        
        self.db_manager.execute_query(query_update, [url_doc.replace(base, ""), aluno])

        # Insere no GED
        query_insert = """
            INSERT INTO DTB_ANCHIETA_PROD.DBO.ANC_SIS_GED_DOCUMENTOS
            VALUES ('22', GETDATE(), ?, ?, NULL)
        """
        self.db_manager.execute_query(
            query_insert,
            [url_doc.replace(base, ""), url_doc]
        )

        # Recupera ID do documento
        query_select = """
            SELECT TOP 1 COD_DOCUMENTO
            FROM DTB_ANCHIETA_PROD.DBO.ANC_SIS_GED_DOCUMENTOS
            WHERE DOCUMENTO = ?
            ORDER BY DATA_DOCUMENTO DESC
        """
        resultado = self.db_manager.fetch_all(query_select, [url_doc.replace(base, "")])

        if not resultado:
            return {"status": False, "Mensagem": "Documento não encontrado após inserção"}

        id_doc = resultado[0]["COD_DOCUMENTO"]

        # Relaciona documento ao usuário
        query_campos = """
            INSERT INTO DTB_ANCHIETA_PROD.DBO.ANC_SIS_GED_DOCUMENTOS_CAMPOS
            VALUES (?, '22', ?)
        """
        self.db_manager.execute_query(query_campos, [id_doc, usuario])

        # Migração e validação final
        resultado_migracao =  self.insert_validation_and_migration({
            "aluno": aluno,
            "id_doc": id_doc,
            "tipo_doc": tipo_doc,
            "api_resposta": api_resposta,
            "is_valid": is_valid,
            "titular": titular,
            "tipo_execute": tipo_doc,
            "tipo_extra": tipo_extra
        })
        
        return {
            "status": True,
            "id_doc": id_doc,
            "migracao_documento": resultado_migracao
        }
    
    def insert_validation_and_migration(self, doc):
        
        result_insere = self.db_manager.insert_document_validation(
            id_doc=doc['id_doc'],
            aluno=doc['aluno'],
            tipo_documento=doc['tipo_doc'],
            response=doc['api_resposta'],
            valido='S' if doc['is_valid'] else 'N',
            titular=doc['titular']
        )

        if doc['is_valid'] == True:
            
            if doc['tipo_extra'] not in [None, '']: 
                migration_result = self._execute_migration(doc['tipo_extra'], doc['api_resposta'], doc['aluno'])
            else:         
                migration_result = self._execute_migration(doc['tipo_doc'], doc['api_resposta'], doc['aluno'])

            result_update = self.db_manager.execute_query('''
                UPDATE A
                SET A.STATUS = 'Entregue',
                    A.QUANTIDADE_ENTREGUE = 1
                FROM LY_DOCUMENTOS_PESSOA a
                inner join (
                        SELECT 
                        A.*,
                        CASE 
                            WHEN A.nome LIKE '%RG DO RESPONS%' THEN 'rg_responsavel'
                            WHEN A.nome LIKE '%CPF DO RESPONS%' THEN 'cpf_responsavel'
                            WHEN A.nome LIKE '%CERTIDÃO DE NASCIMENTO/CASAMENTO%' THEN 'certidao_nascimento/casamento'
                            WHEN A.nome LIKE '%CERTIDÃO DE NASCIMENTO%' THEN 'certidao_nascimento/casamento'
                            WHEN A.nome LIKE '%CERTIFICADO DE CONCLUSÃO DE ENSINO MÉDIO%' THEN 'certificado_conclusao_ensino_medio'
                            WHEN A.nome LIKE '%COMPROVANTE DE RESIDÊNCIA%' THEN 'comprovante_residencia'
                            WHEN A.nome LIKE '%HISTÓRICO ESCOLAR DO ENSINO MÉDIO%' THEN 'historico_escolar'
                            WHEN A.NOME LIKE '%HISTÓRICO ESCOLAR DE GRADUAÇÃO%' THEN 'historico_escolar'
                            WHEN A.NOME LIKE '%HISTÓRICO ESCOLAR DO ENSINO FUNDAMENTAL%' THEN 'historico_escolar_fundamental'
                            WHEN A.NOME LIKE '%HISTÓRICO ESCOLAR DE TRANSFERÊNCIA%' THEN 'historico_escolar_fundamental'
                            WHEN A.nome LIKE '%CPF%' THEN 'cpf'
                            WHEN A.nome LIKE '%RG%' THEN 'rg'
                            WHEN A.nome LIKE '%TITULO DE ELEITOR%' THEN 'titulo_eleitor'
                            WHEN A.NOME LIKE '%CERTIFICADO DE RESERVISTA%' THEN 'certificado_reservista'
                            when A.NOME LIKE '%DIPLOMA DE GRADUAÇÃO%' THEN 'certificado_diploma_graduacao'
                            when A.NOME LIKE '%DECLARAÇÃO DE TRANSFERÊNCIA%' THEN 'declaracao_transferencia'
                        END AS CODIGO_PADRAO
                    FROM LY_DOCUMENTO_PROCESSO A
                ) b on a.ID_DOCUMENTO_PROCESSO = b.id
                left join dtb_anchieta_prod.dbo.ANCHI_DOCUMENTOS_ENTREGUES_VALIDA c
                    on b.CODIGO_PADRAO = c.TIPO_DOCUMENTO AND 
                    A.ALUNO = C.ALUNO
                WHERE A.ALUNO = ? AND c.TIPO_DOCUMENTO = ?
            ''', (doc['aluno'], doc['tipo_doc']))

            result_visto = self.confirm_visto_confere(aluno=doc['aluno'])
        return {
            'insere_validacao': result_insere,
            'migracao_dados': migration_result,
            'atualizacao_status': result_update,
            'visto_confere': result_visto
        }
    
    def _execute_migration(self, tipo_doc: str, data: Dict[str, Any], aluno: str) -> int:
        """
        Executa a migração dos dados para o banco
        
        Args:
            tipo_doc: Tipo do documento
            data: Dados extraídos
            aluno: Código do aluno
            
        Returns:
            Número de linhas afetadas na migração
        """
        try:
            # Obtém a classe de migração apropriada
            migration_class = self.migration_classes.get(tipo_doc)
            
            if not migration_class:
                print(f"Tipo de documento não suportado para migração: {tipo_doc}")
                return False
            
            # Cria instância da migração e executa
            migration = migration_class(self.db_manager)
            
            rows_affected = migration.migrate(data, aluno)

            print(f"Migração executada para {tipo_doc} - {rows_affected} linhas afetadas")
            
            return True
            
        except Exception as e:
            print(f"Erro na migração para {tipo_doc}: {str(e)}")
            return {"ERROR": str(e)}
    
    def confirm_visto_confere(self, aluno):
        try:
            sql = """
                SELECT STATUS
                FROM DTB_LYCEUM_PROD.DBO.LY_DOCUMENTOS_PESSOA A 
                INNER JOIN DTB_LYCEUM_PROD.DBO.LY_DOCUMENTO_PROCESSO B
                    ON A.ID_DOCUMENTO_PROCESSO = B.ID
                WHERE A.ALUNO = ? AND B.DOC IN ('1','25', '6', '9', '2', '10', '4','23','19', '24', '16', '17', '29', '33', '18')"""

            resultado = self.db_manager.fetch_all(sql, (aluno,))
            
        except Exception as e:
            return f"Não foi possível carregar os documentos entregues {e}"
        
        if all(valor['STATUS'] == 'Entregue' for valor in resultado):
            try:
                sql = """
                    UPDATE A
                    SET STATUS = 'Entregue'
                    FROM DTB_LYCEUM_PROD.DBO.LY_DOCUMENTOS_PESSOA A
                    INNER JOIN DTB_LYCEUM_PROD.DBO.LY_DOCUMENTO_PROCESSO B
                        ON A.ID_DOCUMENTO_PROCESSO = B.ID
                    WHERE A.ALUNO = ? AND B.DOC = '28'
                """

                att = self.db_manager.execute_query(sql, (aluno))
                
                if att == True:
                    return {"status": True}
                else:
                    return {"status": False, "Motivo": f"Não foi atualizado: {att}"}
            
            except Exception as e:
                return {"status": False, "Mensagem": f"Não foi possível atualizar o Visto Confere do aluno {aluno} por motivos {e}"}
        else:
            return {"status": True, "Mensagem": f"Nem todos os documentos estão entregues: {resultado}"}
    
    def get_pending_documents(self) -> List[Dict[str, Any]]:
        """
        Busca documentos pendentes de processamento no banco
        
        Returns:
            Lista de documentos pendentes
        """
        # Query para buscar documentos que ainda não foram processados
        # Ajuste esta query conforme sua estrutura de banco
        query = """
           SELECT DISTINCT 
            a.ALUNO,
            CASE 
                WHEN a.UNIDADE_ENSINO IN ('EJND_GRAD', 'EAD_GRAD', 'EJND_HIB_GRAD') THEN 'graduacao'
                WHEN a.UNIDADE_ENSINO LIKE '%POS%' THEN 'pos-graduacao'
                WHEN a.UNIDADE_ENSINO IN ('EJND_ENS_FUND', 'EJND_ENS_MED', 'EJND_ENS_TEC') THEN 'escola'
                ELSE 'graduacao'
            END AS ENSINO,
            'rg' as POSICAO,
            a.ALUNO as USUARIO,
            'https://ged-anchieta.s3.amazonaws.com/'+C.RG AS CAMINHO
        FROM LY_ALUNO A
        JOIN LY_PESSOA B 
            ON B.PESSOA = A.PESSOA
        JOIN dtb_anchieta_prod.dbo.ANCHI_DOCUMENTOS_ENTREGUES C
            ON A.ALUNO = C.ALUNO
        WHERE 
            A.SIT_ALUNO = 'ATIVO'
            AND A.ANO_INGRESSO >= 2020
            AND (
                B.CPF LIKE '%.%-%'
                OR B.RG_NUM LIKE '%.%-%'
            )
            AND RG IS NOT NULL
        
        
        ORDER BY A.ALUNO ASC

        """
        return self.db_manager.fetch_all(query)
    
    def process_all_pending_documents(self) -> Dict[str, Any]:
        """
        Processa todos os documentos pendentes
        
        Returns:
            Relatório do processamento
        """
        print("Iniciando processamento de documentos pendentes...")
        
        # Busca documentos pendentes
        pending_docs = self.get_pending_documents()
        
        if not pending_docs:
            return {
                'status': 'success',
                'message': 'Nenhum documento pendente encontrado',
                'processed_count': 0,
                'results': []
            }
        
        print(f"Encontrados {len(pending_docs)} documentos pendentes")
        
        results = []
        processed_count = 0
        timeout_count = 0
        error_count = 0
        
        # Processa cada documento
        for doc in pending_docs:
            
            result = self.process_document(doc)
            results.append(result)
            #self.mark_document_as_processed(doc['ID_DOCUMENTO'])
            
            if result['status'] == 'success':
                processed_count += 1
            elif result['status'] == 'timeout':
                timeout_count += 1
            elif result['status'] == 'error':
                error_count += 1
            breakpoint()
            # Pequena pausa entre processamentos para não sobrecarregar a API
            
            time.sleep(0.5)
        
        # Prepara mensagem de resultado
        message_parts = []
        if processed_count > 0:
            message_parts.append(f"{processed_count} processados com sucesso")
        if timeout_count > 0:
            message_parts.append(f"{timeout_count} com timeout (serão tentados novamente)")
        if error_count > 0:
            message_parts.append(f"{error_count} com erro")
        
        message = f"Processamento concluído. {', '.join(message_parts)} de {len(pending_docs)} documentos."
        
        return {
            'status': 'completed',
            'message': message,
            'processed_count': processed_count,
            'timeout_count': timeout_count,
            'error_count': error_count,
            'total_count': len(pending_docs),
            'results': results
        }


class DocumentProcessorWeb:
    def __init__(self, database_config: Dict[str, Any]):
        """
        Inicializa o processador
        
        Args:
            database_config: Configurações do banco de dados
        """
        self.db_manager = DatabaseManager(database_config)
        self.gemi = Gemini()
        # Configura o API client com timeout maior e retry para lidar com timeouts
        # self.api_client = APIClient(timeout=60, max_retries=3, retry_delay=10)
        
        # Mapeamento de tipos de documento para classes de migração
        self.migration_classes = {
            'rg': RGMigration,
            #'cnh': CNHMigration,
            'cpf': CPFMigration,
            'rg_aluno': RGMigration,
            'cpf_aluno': CPFMigration,
            'certidao_nascimento': CertidaoNascimentoMigration,
            'certidao_casamento': CertidaoCasamentoMigration,
            'comprovante_residencia': ComprovanteResidenciaMigration,
            'certificado_conclusao_ensino_medio': CertificadoMedioMigration,
            'certificado_diploma_graduacao': CertificadoGraduacaoMigration,
            'historico_escolar': HistoricoEscolarMigration,
            'historico_escolar_fundamental': HistoricoFundamentalMigration,
            'carteira_vacinação': CarteiraVacinacaoMigration,
            'certificado_reservista': CertificadoReservistaMigration,
            'rg_responsavel': DocumentosResponsavelMigration,
            'cpf_responsavel': DocumentosResponsavelMigration,
            'titulo_eleitor': TituloEleitorMigration,
            'declaracao_transferencia': DeclaracaoTransferenciaMigration
        }
        self.MAPA_DOCUMENTOS = {
            "escola": {
                'certidao_nascimento/casamento': "CERT_NASCIMENTO",
                'rg': "RG",
                'cpf': "CPF",
                'historico_transf': "HISTORICO_ESCOLAR",
                'declaracao_transf': "DECL_TRANSFERENCIA",
                'comprovante_residencia': "COMP_RESIDENCIA",
                'rg_responsavel': "RG_RESPONSAVEL",
                'cpf_responsavel': "CPF_RESPONSAVEL",
                'historico_escolar_fundamental': "HISTORICO_FUNDAMENTAL",
                'cartao_vacina': "CARTEIRA_VACINA"
            },
            "graduacao": {
                'certidao_nascimento/casamento': "CERT_NASCIMENTO",
                'certificado_conclusao_ensino_medio': "CERT_CONC_EN_MEDIO",
                'cert_reservista': "CERT_RESERVISTA",
                'comprovante_residencia': "COMP_RESIDENCIA",
                'cpf': "CPF",
                'historico_escolar': "HISTORICO_ESCOLAR",
                'rg': "RG",
                'titulo_eleitor': "TITULO_ELEITOR"
            },
            "pos_graduacao": {
                'certidao_nascimento/casamento': "CERT_NASCIMENTO",
                'comprovante_residencia': "COMP_RESIDENCIA",
                'cpf': "CPF",
                'certificado_diploma_graduacao': "DIPLOMA_GRADUACAO",
                'historico_escolar': "HISTORICO_ESCOLAR",
                'rg': "RG"
            }
        }


    def process_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa um documento individual
        
        Args:
            document: Dados do documento
            
        Returns:
            Resultado do processamento
        """
        # Extrai dados do documento
        aluno = document['ALUNO']
        url_doc = document['DOC']
        usuario = document['usuario']
        posicao = document['posicao']
        curso_entrega = document['curso_entrega']

        base = "https://ged-anchieta.s3.amazonaws.com/"

        #tipo_doc = self._determine_wich_document(curso_entrega, posicao)
        tipo_doc =  posicao

        try:
            if tipo_doc in ('rg_responsavel', 'cpf_responsavel'):
                if 'rg' in tipo_doc:
                    api_resposta = self.gemi.analisarDocumento(url=url_doc, origem=curso_entrega, tipo_doc='rg')
                else:
                    api_resposta = self.gemi.analisarDocumento(url=url_doc, origem=curso_entrega, tipo_doc='cpf')
            else:
                api_resposta = self.gemi.analisarDocumento(url=url_doc, origem=curso_entrega, tipo_doc=tipo_doc)

            if api_resposta.get('Erro'):
                return {
                    "status": "error",
                    'message': 'Erro ao se conectar com a IA',
                    'api_resposta': api_resposta
                }
            
            validacao = api_resposta.get('validacao', {})
            extracao = api_resposta.get('extracao', {})

            # Verifica se a API retornou dados válidos
            if validacao.get('is_valid') == True and extracao:
                if tipo_doc == 'certidao_nascimento/casamento':
                    match validacao['document_type']:
                        case 'certidao_nascimento':
                            is_valid = self._determine_document_validity(extracao, 'certidao_nascimento')
                            titular = extracao['fields'].get('nome_pessoa')
                            tipo_extra = 'certidao_nascimento'
                        case 'certidao_casamento':
                            is_valid = self._determine_document_validity(extracao, 'certidao_casamento')
                            titular = None
                            tipo_extra = 'certidao_casamento'
                        case _:
                            is_valid = False
                            titular = None
                            tipo_extra = None

                else:
                    is_valid = self._determine_document_validity(extracao, tipo_doc)

                    titular = extracao['fields'].get('nome_pessoa')
                    tipo_extra = None

                if is_valid == True:

                    resposta = self.insert_document_delivery(
                        aluno=aluno,
                        url_doc=url_doc,
                        curso_entrega=curso_entrega,
                        posicao=posicao,
                        usuario=usuario,
                        tipo_doc=tipo_doc,
                        api_resposta=extracao,
                        is_valid=is_valid,
                        titular=titular,
                        base=base,
                        tipo_extra=tipo_extra
                    )

                    if resposta['status'] == True:
                        return {'status': "sucesso", "Documento": resposta}
                    else:
                        return {'status': "error", "Documento": resposta}
                else:
                    return {'status': "error", 'message': 'Documento considerado inválido pela validação interna', "respostaIA": api_resposta}
            else:
                result_insere = self.db_manager.insert_document_validation(
                    id_doc=None,
                    aluno=aluno,
                    tipo_documento=tipo_doc,
                    response=api_resposta,
                    valido='N',
                    titular=aluno
                )
                return {
                    "status": "error",
                    'message': 'Resposta vazia da API ou documento inválido',
                    'api_resposta': api_resposta
                }

        except Exception as e:
            # Verifica se é um erro de timeout ou 504
            is_timeout_error = (
                'timeout' in str(e).lower() or
                '504' in str(e) or
                'endpoint request timed out' in str(e).lower()
            )

            if is_timeout_error:
                return {
                    'status': 'error',
                    'status': 'timeout',
                    'retry_needed': True
                }

            return {
                "status": "error",
                'message': str(e),
                'api_resposta': api_resposta,
                'retry_needed': False
            }
    
    '''def _determine_wich_document(self, curso, posicao):
        match curso:
            case "escola":
                match posicao:
                    case 'certidao_nascimento/casamento':
                        return "certidao_nascimento/casamento"
                    case 'rg_aluno':
                        return "rg"
                    case 'cpf_aluno':
                        return "cpf"
                    case 'historico_transf':
                        return "historico_escolar"
                    case 'declaracao_transf':
                        return "declaracao_transferencia"
                    case 'comprovante' :
                        return "comprovante_residencia"
                    case 'rg_responsavel':
                        return "rg_responsavel"
                    case 'cpf_responsavel':
                        return "cpf_responsavel"
                    case 'historico_fund':
                        return "historico_escolar_fundamental"
                    case 'carteira_vacina':
                        return "carteira_vacinacao"
                    case _:
                        return posicao
            case "graduacao":
                match posicao:
                    case 'certidao_nascimento/casamento':
                        return "certidao_nascimento/casamento"
                    case 'certificado_conclusao_ensino_medio':
                        return "certificado_conclusao_ensino_medio"
                    case 'cert_reservista':
                        return "certificado_reservista"
                    case 'comprovante_residencia':
                        return "comprovante_residencia"
                    case 'cpf':
                        return "cpf"
                    case 'historico_escolar':
                        return "historico_escolar"
                    case 'rg':
                        return "rg"
                    case 'titulo_eleitor':
                        return "titulo_eleitor"
                    case _:
                        return posicao
            case "pos_graduacao":
                match posicao:
                    case 'certidao':
                        return "certidao_nascimento/casamento"
                    case 'comprovante':
                        return "comprovante_residencia"
                    case 'cpf':
                        return "cpf"
                    case 'diploma':
                        return "certificado_diploma_graduacao"
                    case 'historico':
                        return "historico_escolar"
                    case 'rg':
                        return "rg"
                    case _:
                        return posicao'''

    def _determine_document_validity(self, data: Dict[str, Any], tipo_doc: str) -> bool:
        """
        Determina se um documento é válido baseado nos dados extraídos
        
        Args:
            data: Dados extraídos do documento
            tipo_doc: Tipo do documento
            
        Returns:
            True se o documento é válido, False caso contrário
        """
        # Validações básicas por tipo de documento
       
        if tipo_doc == 'rg' or tipo_doc == 'rg_responsavel':
            # Para documentos de identificação, verifica se tem nome e número
            if data.get('is_valid') == False or data.get('is_valid') is None and data['document_type'] not in ('rg', 'cnh'):
                return False
            else:
                return bool(data['fields'].get('rg') and data['fields'].get('nome_pessoa')) 
                            
        elif tipo_doc == 'cpf' or tipo_doc == 'cpf_responsavel':
            # Para documentos de identificação, verifica se tem nome e número
            if data.get('is_valid') == False or data.get('is_valid') is None and data['document_type'] not in ('rg', 'cnh', 'cpf'):
                return False
            else:
                return bool(data['fields'].get('cpf') and data['fields'].get('nome_pessoa'))           
                
        elif tipo_doc == 'cnh':
            # Para documentos de identificação, verifica se tem nome e número
            if data.get('is_valid') == False or data.get('is_valid') is None and data['document_type'] not in ('rg', 'cnh'):
                return False
            else:
                return bool(data['fields'].get('cpf') and data['fields'].get('nome_pessoa') and data['fields'].get('rg') and data['fields'].get('data_nascimento') and data['fields'].get('nome_pai') and data['fields'].get('nome_mae'))
                
        elif tipo_doc in ['certidao_nascimento']:
            # Para certidões, verifica se tem nome
            if data.get('is_valid') == False or data.get('is_valid') is None and data['document_type'] not in ('certidao_nascimento'):
                return False
            else:
                return bool(data['fields'].get('nome_pessoa') and data['fields'].get('data_nascimento') and data['fields'].get('cidade_nascimento'))
        
        elif tipo_doc in ['certidao_casamento']:
            if data.get('is_valid') == False or data.get('is_valid') is None and data['document_type'] not in ('certidao_casamento'):
                return False
            else:
                return bool(data['fields'].get('nome_noivo_pos_casamento') and data['fields'].get('data_casamento') and data['fields'].get('nome_noiva_pos_casamento'))
        
        elif tipo_doc == 'comprovante_residencia':
            # Para comprovante, verifica se tem CEP e endereço
            if data.get('is_valid') == False or data.get('is_valid') is None and data['document_type'] not in ('comprovante_residencia'):
                return False
            else:
                return bool(data['fields'].get('cep') and data['fields'].get('endereco'))
        
        elif tipo_doc in ['certificado_conclusao_ensino_medio']:
            
            if (data.get('is_valid') == False or data.get('is_valid') is None)  and data['document_type'] not in ('conclusao_historico'):
                return False
            else:
                if data.get('origem_entrega') == 'graduacao' and data['fields'].get('conclusao', '') != '':
                    return bool(data['fields']['conclusao'].get('instituicao_ensino') and data['fields'].get('nome_pessoa') and data['fields']['conclusao'].get('ano_conclusao'))
                else:
                    return False
                
        elif tipo_doc in ['certificado_diploma_graduacao']:
            
            if (data.get('is_valid') == False or data.get('is_valid') is None) and data['document_type'] not in ('conclusao_historico'):
                return False
            else:
                if data.get('origem_entrega') == 'pos_graduacao'  and data['fields'].get('conclusao', '') != '':
                    return bool(data['fields']['conclusao'].get('instituicao_ensino') and data['fields'].get('nome_pessoa') and data['fields']['conclusao'].get('ano_conclusao'))
                else:
                    return False
                
        elif tipo_doc in ['historico_escolar_fundamental']:
            if (data.get('is_valid') == False or data.get('is_valid') is None) and data['document_type'] not in ('conclusao_historico'):
                return False
            else:
                if data.get('origem_entrega') == 'escola' and data['fields'].get('conclusao', '') != '' :
                    return bool(data['fields']['historico'].get('instituicao_ensino') and data['fields'].get('nome_pessoa'))
                else:
                    return False
                
        elif tipo_doc in ['historico_escolar']:           
            if (data.get('is_valid') == False or data.get('is_valid') is None) and data['fields'].get('historico', '') == '' and data['document_type'] not in ('conclusao_historico'):
                return False
            else:
                if data.get('origem_entrega') == 'graduacao' or data.get('origem_entrega') == 'pos_graduacao':
                    return bool(data['fields']['historico'].get('instituicao_ensino') and data['fields'].get('nome_pessoa'))
                else:
                    return False
                
        elif tipo_doc in ['declaracao_transferencia']:
            if (data.get('is_valid') == False or data.get('is_valid') is None) and data.get('origem_entrega') != 'escola' and data['document_type'] not in ('declaracao_transferencia'):
                return False
            else:
                return bool(data['fields'].get('nome_pessoa') and data['fields'].get('instituicao_origem') and data['fields'].get('data_emissao'))
            
        elif tipo_doc == 'carteira_vacinacao':  
            # Para carteira de vacinação, verifica se tem nome e número da carteira
            if data.get('is_valid') == False or data.get('is_valid') is None:
                return False
            else:
                return True
        
        elif tipo_doc == 'certificado_reservista':
            # Para certificado reservista, verifica se tem nome e número de alistamento
            if data.get('is_valid') == False or data.get('is_valid') is None and data['document_type'] not in ('certificado_reservista'):
                return False
            else:
                return bool(data['fields'].get('nome_pessoa') and data['fields'].get('ra') and data['fields'].get('cpf'))
        
        elif tipo_doc == 'titulo_eleitor':
            # Para título de eleitor, verifica se tem nome e número do título
            if data.get('is_valid') == False or data.get('is_valid') is None and data['document_type'] not in ('titulo_eleitor'):
                return False
            else:
                return bool(data['fields'].get('nome_pessoa') and data['fields'].get('data_nascimento') and data['fields'].get('municipio')
                            and data['fields'].get('estado') and data['fields'].get('zona') and data['fields'].get('secao') 
                            and data['fields'].get('data_emissao') and data['fields'].get('numero_titulo')
                        )

    def insert_document_delivery(self, aluno, url_doc, curso_entrega, posicao, usuario, tipo_doc, api_resposta, is_valid, titular, base, tipo_extra=None):
        coluna = self.MAPA_DOCUMENTOS.get(curso_entrega, {}).get(posicao)
        if not coluna:
            return {"status": False, "Mensagem": "Curso ou posição inválida"}
        
        # Atualiza documento do aluno
        query_update = f"""
            UPDATE DTB_ANCHIETA_PROD.DBO.ANCHI_DOCUMENTOS_ENTREGUES
            SET {coluna} = ?
            WHERE ALUNO = ?
            AND ATIVO = '1'
        """
        
        self.db_manager.execute_query(query_update, [url_doc.replace(base, ""), aluno])

        # Insere no GED
        query_insert = """
            INSERT INTO DTB_ANCHIETA_PROD.DBO.ANC_SIS_GED_DOCUMENTOS
            VALUES ('22', GETDATE(), ?, ?, NULL)
        """
        self.db_manager.execute_query(
            query_insert,
            [url_doc.replace(base, ""), url_doc]
        )

        # Recupera ID do documento
        query_select = """
            SELECT TOP 1 COD_DOCUMENTO
            FROM DTB_ANCHIETA_PROD.DBO.ANC_SIS_GED_DOCUMENTOS
            WHERE DOCUMENTO = ?
            ORDER BY DATA_DOCUMENTO DESC
        """
        resultado = self.db_manager.fetch_all(query_select, [url_doc.replace(base, "")])

        if not resultado:
            return {"status": False, "Mensagem": "Documento não encontrado após inserção"}

        id_doc = resultado[0]["COD_DOCUMENTO"]

        # Relaciona documento ao usuário
        query_campos = """
            INSERT INTO DTB_ANCHIETA_PROD.DBO.ANC_SIS_GED_DOCUMENTOS_CAMPOS
            VALUES (?, '22', ?)
        """
        self.db_manager.execute_query(query_campos, [id_doc, usuario])

        # Migração e validação final
        resultado_migracao =  self.insert_validation_and_migration({
            "aluno": aluno,
            "id_doc": id_doc,
            "tipo_doc": tipo_doc,
            "api_resposta": api_resposta,
            "is_valid": is_valid,
            "titular": titular,
            "tipo_execute": tipo_doc,
            "tipo_extra": tipo_extra
        })
        
        return {
            "status": True,
            "id_doc": id_doc,
            "migracao_documento": resultado_migracao
        }
    
    def insert_validation_and_migration(self, doc):
        
        result_insere = self.db_manager.insert_document_validation(
            id_doc=doc['id_doc'],
            aluno=doc['aluno'],
            tipo_documento=doc['tipo_doc'],
            response=doc['api_resposta'],
            valido='S' if doc['is_valid'] else 'N',
            titular=doc['titular']
        )

        if doc['is_valid'] == True:
            
            if doc['tipo_extra'] not in [None, '']: 
                migration_result = self._execute_migration(doc['tipo_extra'], doc['api_resposta'], doc['aluno'])
            else:         
                migration_result = self._execute_migration(doc['tipo_doc'], doc['api_resposta'], doc['aluno'])

            result_update = self.db_manager.execute_query('''
                UPDATE A
                SET A.STATUS = 'Entregue',
                    A.QUANTIDADE_ENTREGUE = 1
                FROM LY_DOCUMENTOS_PESSOA a
                inner join (
                        SELECT 
                        A.*,
                        CASE 
                            WHEN A.nome LIKE '%RG DO RESPONS%' THEN 'rg_responsavel'
                            WHEN A.nome LIKE '%CPF DO RESPONS%' THEN 'cpf_responsavel'
                            WHEN A.nome LIKE '%CERTIDÃO DE NASCIMENTO/CASAMENTO%' THEN 'certidao_nascimento/casamento'
                            WHEN A.nome LIKE '%CERTIDÃO DE NASCIMENTO%' THEN 'certidao_nascimento/casamento'
                            WHEN A.nome LIKE '%CERTIFICADO DE CONCLUSÃO DE ENSINO MÉDIO%' THEN 'certificado_conclusao_ensino_medio'
                            WHEN A.nome LIKE '%COMPROVANTE DE RESIDÊNCIA%' THEN 'comprovante_residencia'
                            WHEN A.nome LIKE '%HISTÓRICO ESCOLAR DO ENSINO MÉDIO%' THEN 'historico_escolar'
                            WHEN A.NOME LIKE '%HISTÓRICO ESCOLAR DE GRADUAÇÃO%' THEN 'historico_escolar'
                            WHEN A.NOME LIKE '%HISTÓRICO ESCOLAR DO ENSINO FUNDAMENTAL%' THEN 'historico_escolar_fundamental'
                            WHEN A.NOME LIKE '%HISTÓRICO ESCOLAR DE TRANSFERÊNCIA%' THEN 'historico_escolar_fundamental'
                            WHEN A.nome LIKE '%CPF%' THEN 'cpf'
                            WHEN A.nome LIKE '%RG%' THEN 'rg'
                            WHEN A.nome LIKE '%TITULO DE ELEITOR%' THEN 'titulo_eleitor'
                            WHEN A.NOME LIKE '%CERTIFICADO DE RESERVISTA%' THEN 'certificado_reservista'
                            when A.NOME LIKE '%DIPLOMA DE GRADUAÇÃO%' THEN 'certificado_diploma_graduacao'
                            when A.NOME LIKE '%DECLARAÇÃO DE TRANSFERÊNCIA%' THEN 'declaracao_transferencia'
                        END AS CODIGO_PADRAO
                    FROM LY_DOCUMENTO_PROCESSO A
                ) b on a.ID_DOCUMENTO_PROCESSO = b.id
                left join dtb_anchieta_prod.dbo.ANCHI_DOCUMENTOS_ENTREGUES_VALIDA c
                    on b.CODIGO_PADRAO = c.TIPO_DOCUMENTO AND 
                    A.ALUNO = C.ALUNO
                WHERE A.ALUNO = ? AND c.TIPO_DOCUMENTO = ?
            ''', (doc['aluno'], doc['tipo_doc']))

            result_visto = self.confirm_visto_confere(aluno=doc['aluno'])
        else:
            result_update = self.db_manager.execute_query('''
                UPDATE A
                SET A.STATUS = 'Inválido',
                    A.QUANTIDADE_ENTREGUE = 1
                FROM LY_DOCUMENTOS_PESSOA a
                inner join (
                    SELECT 
                        A.*,
                        CASE 
                            WHEN A.nome LIKE '%RG DO RESPONS%' THEN 'rg_responsavel'
                            WHEN A.nome LIKE '%CPF DO RESPONS%' THEN 'cpf_responsavel'
                            WHEN A.nome LIKE '%CERTIDÃO DE NASCIMENTO/CASAMENTO%' THEN 'certidao_nascimento/casamento'
                            WHEN A.nome LIKE '%CERTIDÃO DE NASCIMENTO%' THEN 'certidao_nascimento/casamento'
                            WHEN A.nome LIKE '%CERTIFICADO DE CONCLUSÃO DE ENSINO MÉDIO%' THEN 'certificado_conclusao_ensino_medio'
                            WHEN A.nome LIKE '%COMPROVANTE DE RESIDÊNCIA%' THEN 'comprovante_residencia'
                            WHEN A.nome LIKE '%HISTÓRICO ESCOLAR DO ENSINO MÉDIO%' THEN 'historico_escolar'
                            WHEN A.NOME LIKE '%HISTÓRICO ESCOLAR DE GRADUAÇÃO%' THEN 'historico_escolar'
                            WHEN A.NOME LIKE '%HISTÓRICO ESCOLAR DO ENSINO FUNDAMENTAL%' THEN 'historico_escolar_fundamental'
                            WHEN A.NOME LIKE '%HISTÓRICO ESCOLAR DE TRANSFERÊNCIA%' THEN 'historico_escolar_fundamental'
                            WHEN A.nome LIKE '%CPF%' THEN 'cpf'
                            WHEN A.nome LIKE '%RG%' THEN 'rg'
                            WHEN A.nome LIKE '%TITULO DE ELEITOR%' THEN 'titulo_eleitor'
                            WHEN A.NOME LIKE '%CERTIFICADO DE RESERVISTA%' THEN 'certificado_reservista'
                            when A.NOME LIKE '%DIPLOMA DE GRADUAÇÃO%' THEN 'certificado_diploma_graduacao'
                            when A.NOME LIKE '%DECLARAÇÃO DE TRANSFERÊNCIA%' THEN 'declaracao_transferencia'
                        END AS CODIGO_PADRAO
                    FROM LY_DOCUMENTO_PROCESSO A
                ) b on a.ID_DOCUMENTO_PROCESSO = b.id
                left join dtb_anchieta_prod.dbo.ANCHI_DOCUMENTOS_ENTREGUES_VALIDA c
                    on b.CODIGO_PADRAO = c.TIPO_DOCUMENTO AND 
                    A.ALUNO = C.ALUNO
                WHERE A.ALUNO = ? AND c.TIPO_DOCUMENTO = ?
            ''', (doc['aluno'], doc['tipo_doc']))
        
        return {
            'insere_validacao': result_insere,
            'migracao_dados': migration_result,
            'atualizacao_status': result_update,
            'visto_confere': result_visto
        }
    
    def _execute_migration(self, tipo_doc: str, data: Dict[str, Any], aluno: str) -> int:
        """
        Executa a migração dos dados para o banco
        
        Args:
            tipo_doc: Tipo do documento
            data: Dados extraídos
            aluno: Código do aluno
            
        Returns:
            Número de linhas afetadas na migração
        """
        try:
            # Obtém a classe de migração apropriada
            migration_class = self.migration_classes.get(tipo_doc)
            
            if not migration_class:
                print(f"Tipo de documento não suportado para migração: {tipo_doc}")
                return False
            
            # Cria instância da migração e executa
            migration = migration_class(self.db_manager)
            
            rows_affected = migration.migrate(data, aluno)

            print(f"Migração executada para {tipo_doc} - {rows_affected} linhas afetadas")
            
            return True
            
        except Exception as e:
            print(f"Erro na migração para {tipo_doc}: {str(e)}")
            return 0
    
    def confirm_visto_confere(self, aluno):
        try:
            sql = """
                SELECT STATUS
                FROM DTB_LYCEUM_PROD.DBO.LY_DOCUMENTOS_PESSOA A 
                INNER JOIN DTB_LYCEUM_PROD.DBO.LY_DOCUMENTO_PROCESSO B
                    ON A.ID_DOCUMENTO_PROCESSO = B.ID
                WHERE A.ALUNO = ? AND B.DOC IN ('1','25', '6', '9', '2', '10', '4','23','19', '24', '16', '17', '29', '33', '18')"""

            resultado = self.db_manager.fetch_all(sql, (aluno,))
            
        except Exception as e:
            return f"Não foi possível carregar os documentos entregues {e}"
        
        if all(valor['STATUS'] == 'Entregue' for valor in resultado):
            try:
                sql = """
                    UPDATE A
                    SET STATUS = 'Entregue'
                    FROM DTB_LYCEUM_PROD.DBO.LY_DOCUMENTOS_PESSOA A
                    INNER JOIN DTB_LYCEUM_PROD.DBO.LY_DOCUMENTO_PROCESSO B
                        ON A.ID_DOCUMENTO_PROCESSO = B.ID
                    WHERE A.ALUNO = ? AND B.DOC = '28'
                """

                att = self.db_manager.execute_query(sql, (aluno))
                
                if att == True:
                    return {"status": True}
                else:
                    return {"status": False, "Motivo": f"Não foi atualizado: {att}"}
            
            except Exception as e:
                return {"status": False, "Mensagem": f"Não foi possível atualizar o Visto Confere do aluno {aluno} por motivos {e}"}
        else:
            return {"status": True, "Mensagem": f"Nem todos os documentos estão entregues: {resultado}"}

    def process_pending_document(self, aluno, documento, curso_entrega, posicao, usuario):
        doc = {'ALUNO': aluno, 'DOC': documento, "curso_entrega": curso_entrega, "posicao": posicao, "usuario": usuario}
        return self.process_document(doc)
        
def main(payload):
    """
    Função principal simplificada
    """
    # Configuração do banco de dados
    database_config = {
        'host': '192.168.0.9',
        'database': 'dtb_lyceum_prod',
        'user': 'lyceum',
        'password': 'lyceum',
        'port': 1433
    }
    
    # Inicializa o processador
    processor = DocumentProcessorWeb(database_config)
    
    try:
        # Processa todos os documentos pendentes
        result = processor.process_pending_document(aluno=payload['aluno'], 
                documento=payload['arquivo'], 
                curso_entrega=payload['curso_entrega'], 
                usuario=payload['usuario'], 
                posicao=payload['posicao'])
    
        return result 
    
    except Exception as e:
        
        return {
            "status": "error",
            "mensagem": str(e)
        }