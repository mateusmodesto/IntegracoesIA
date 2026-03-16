#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema Simplificado de Processamento de Documentos
Método main que busca documentos no banco, processa via API e atualiza dados
"""

from typing import Dict, Any
from shared.config import get_logger
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

logger = get_logger(__name__)

# Mapeamento de posicao/curso para coluna no banco de dados
MAPA_DOCUMENTOS = {
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
        'conclusao_historico': "HISTORICO_ESCOLAR",
        'rg': "RG",
        'titulo_eleitor': "TITULO_ELEITOR"
    },
    "pos_graduacao": {
        'certidao_nascimento/casamento': "CERT_NASCIMENTO",
        'comprovante_residencia': "COMP_RESIDENCIA",
        'cpf': "CPF",
        'certificado_diploma_graduacao': "DIPLOMA_GRADUACAO",
        "conclusao_historico": "HISTORICO_ESCOLAR",
        'rg': "RG"
    }
}

# Mapeamento de tipos de documento para classes de migração
MIGRATION_CLASSES = {
    'rg': RGMigration,
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
    'conclusao_historico': HistoricoEscolarMigration,
    'carteira_vacinação': CarteiraVacinacaoMigration,
    'certificado_reservista': CertificadoReservistaMigration,
    'rg_responsavel': DocumentosResponsavelMigration,
    'cpf_responsavel': DocumentosResponsavelMigration,
    'titulo_eleitor': TituloEleitorMigration,
    'declaracao_transferencia': DeclaracaoTransferenciaMigration
}

# Query reutilizada para atualizar status do documento no LY_DOCUMENTOS_PESSOA
# via mapeamento CASE WHEN do LY_DOCUMENTO_PROCESSO
STATUS_UPDATE_QUERY = '''
    UPDATE A
    SET A.STATUS = ?,
        A.QUANTIDADE_ENTREGUE = 1
    FROM DTB_LYCEUM_PROD.DBO.LY_DOCUMENTOS_PESSOA a
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
                WHEN A.NOME LIKE '%HISTÓRICO ESCOLAR DO ENSINO MÉDIO%' THEN 'conclusao_historico'
                WHEN A.NOME LIKE '%HISTÓRICO ESCOLAR DE GRADUAÇÃO%' THEN 'conclusao_historico'
                WHEN A.NOME LIKE '%HISTÓRICO ESCOLAR DO ENSINO FUNDAMENTAL%' THEN 'historico_escolar_fundamental'
                WHEN A.NOME LIKE '%HISTÓRICO ESCOLAR DE TRANSFERÊNCIA%' THEN 'historico_escolar_fundamental'
                WHEN A.nome LIKE '%CPF%' THEN 'cpf'
                WHEN A.nome LIKE '%RG%' THEN 'rg'
                WHEN A.nome LIKE '%TITULO DE ELEITOR%' THEN 'titulo_eleitor'
                WHEN A.NOME LIKE '%CERTIFICADO DE RESERVISTA%' THEN 'certificado_reservista'
                when A.NOME LIKE '%DIPLOMA DE GRADUAÇÃO%' THEN 'certificado_diploma_graduacao'
                when A.NOME LIKE '%DECLARAÇÃO DE TRANSFERÊNCIA%' THEN 'declaracao_transferencia'
            END AS CODIGO_PADRAO
        FROM DTB_LYCEUM_PROD.DBO.LY_DOCUMENTO_PROCESSO A
    ) b on a.ID_DOCUMENTO_PROCESSO = b.id
    left join dtb_anchieta_prod.dbo.ANCHI_DOCUMENTOS_ENTREGUES_VALIDA c
        on b.CODIGO_PADRAO = c.TIPO_DOCUMENTO AND
        A.ALUNO = C.ALUNO
    WHERE A.ALUNO = ? AND c.TIPO_DOCUMENTO = ?
'''


class DocumentProcessorWeb:
    """Processador de documentos para chamadas via API web."""

    def __init__(self, database_config: Dict[str, Any]):
        self.db_manager = DatabaseManager(database_config)
        self.gemi = Gemini()
        self.migration_classes = MIGRATION_CLASSES
        self.MAPA_DOCUMENTOS = MAPA_DOCUMENTOS

    def process_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa um documento individual.

        Args:
            document: Dados do documento (ALUNO, DOC, usuario, posicao, curso_entrega)

        Returns:
            Resultado do processamento
        """
        aluno = document['ALUNO']
        url_doc = document['DOC']
        usuario = document['usuario']
        posicao = document['posicao']
        curso_entrega = document['curso_entrega']

        base = "https://ged-anchieta.s3.amazonaws.com/"
        tipo_doc = posicao
        api_resposta = None

        try:
            if tipo_doc in ('rg_responsavel', 'cpf_responsavel'):
                tipo_api = 'rg' if 'rg' in tipo_doc else 'cpf'
                api_resposta = self.gemi.analisarDocumento(url=url_doc, origem=curso_entrega, tipo_doc=tipo_api)
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

            if validacao.get('is_valid') and extracao:
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

                if is_valid:
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

                    if resposta['status']:
                        return {'status': "sucesso", "Documento": resposta}
                    else:
                        return {'status': "error", "Documento": resposta}
                else:
                    self.db_manager.insert_document_validation(
                        id_doc=None,
                        aluno=aluno,
                        tipo_documento=tipo_doc,
                        response=api_resposta,
                        valido='N',
                        titular=aluno
                    )
                    return {
                        'status': "error",
                        'message': 'Documento considerado inválido pela validação interna',
                        "respostaIA": api_resposta
                    }
            else:
                self.db_manager.insert_document_validation(
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
            is_timeout_error = (
                'timeout' in str(e).lower() or
                '504' in str(e) or
                'endpoint request timed out' in str(e).lower()
            )

            if is_timeout_error:
                return {
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
        Determina se um documento é válido baseado nos dados extraídos.

        Args:
            data: Dados extraídos do documento
            tipo_doc: Tipo do documento

        Returns:
            True se o documento é válido, False caso contrário
        """
        if tipo_doc in ('rg', 'rg_responsavel'):
            if data.get('is_valid') is False or (data.get('is_valid') is None and data['document_type'] not in ('rg', 'cnh')):
                return False
            return bool(data['fields'].get('rg') and data['fields'].get('nome_pessoa'))

        elif tipo_doc in ('cpf', 'cpf_responsavel'):
            if data.get('is_valid') is False or (data.get('is_valid') is None and data['document_type'] not in ('rg', 'cnh', 'cpf')):
                return False
            return bool(data['fields'].get('cpf') and data['fields'].get('nome_pessoa'))

        elif tipo_doc == 'cnh':
            if data.get('is_valid') is False or (data.get('is_valid') is None and data['document_type'] not in ('rg', 'cnh')):
                return False
            return bool(
                data['fields'].get('cpf') and data['fields'].get('nome_pessoa')
                and data['fields'].get('rg') and data['fields'].get('data_nascimento')
                and data['fields'].get('nome_pai') and data['fields'].get('nome_mae')
            )

        elif tipo_doc == 'certidao_nascimento':
            if data.get('is_valid') is False or (data.get('is_valid') is None and data['document_type'] not in ('certidao_nascimento',)):
                return False
            return bool(
                data['fields'].get('nome_pessoa')
                and data['fields'].get('data_nascimento')
                and data['fields'].get('cidade_nascimento')
            )

        elif tipo_doc == 'certidao_casamento':
            if data.get('is_valid') is False or (data.get('is_valid') is None and data['document_type'] not in ('certidao_casamento',)):
                return False
            return bool(
                data['fields'].get('nome_noivo_pos_casamento')
                and data['fields'].get('data_casamento')
                and data['fields'].get('nome_noiva_pos_casamento')
            )

        elif tipo_doc == 'comprovante_residencia':
            if data.get('is_valid') is False or (data.get('is_valid') is None and data['document_type'] not in ('comprovante_residencia',)):
                return False
            return bool(data['fields'].get('cep') and data['fields'].get('endereco'))

        elif tipo_doc == 'certificado_conclusao_ensino_medio':
            if (data.get('is_valid') is False or data.get('is_valid') is None) and data['document_type'] not in ('conclusao_historico',):
                return False
            if data.get('origem_entrega') == 'graduacao' and data['fields'].get('conclusao', '') != '':
                return bool(
                    data['fields']['conclusao'].get('instituicao_ensino')
                    and data['fields'].get('nome_pessoa')
                    and data['fields']['conclusao'].get('ano_conclusao')
                )
            return False

        elif tipo_doc == 'certificado_diploma_graduacao':
            if (data.get('is_valid') is False or data.get('is_valid') is None) and data['document_type'] not in ('conclusao_historico',):
                return False
            if data.get('origem_entrega') == 'pos_graduacao' and data['fields'].get('conclusao', '') != '':
                return bool(
                    data['fields']['conclusao'].get('instituicao_ensino')
                    and data['fields'].get('nome_pessoa')
                    and data['fields']['conclusao'].get('ano_conclusao')
                )
            return False

        elif tipo_doc == 'historico_escolar_fundamental':
            if (data.get('is_valid') is False or data.get('is_valid') is None) and data['document_type'] not in ('conclusao_historico',):
                return False
            if data.get('origem_entrega') == 'escola' and data['fields'].get('conclusao', '') != '':
                return bool(
                    data['fields']['historico'].get('instituicao_ensino')
                    and data['fields'].get('nome_pessoa')
                )
            return False

        elif tipo_doc in ('historico_escolar', 'conclusao_historico'):
            if (data.get('is_valid') is False or data.get('is_valid') is None) and data['fields'].get('historico', '') == '' and data['document_type'] not in ('conclusao_historico',):
                return False
            if data.get('origem_entrega') in ('graduacao', 'pos_graduacao'):
                return bool(
                    data['fields']['historico'].get('instituicao_ensino')
                    and data['fields'].get('nome_pessoa')
                )
            return False

        elif tipo_doc == 'declaracao_transferencia':
            if (data.get('is_valid') is False or data.get('is_valid') is None) and data.get('origem_entrega') != 'escola' and data['document_type'] not in ('declaracao_transferencia',):
                return False
            return bool(
                data['fields'].get('nome_pessoa')
                and data['fields'].get('instituicao_origem')
                and data['fields'].get('data_emissao')
            )

        elif tipo_doc == 'carteira_vacinacao':
            if data.get('is_valid') is False or data.get('is_valid') is None:
                return False
            return True

        elif tipo_doc == 'certificado_reservista':
            if data.get('is_valid') is False or (data.get('is_valid') is None and data['document_type'] not in ('certificado_reservista',)):
                return False
            return bool(
                data['fields'].get('nome_pessoa')
                and data['fields'].get('ra')
                and data['fields'].get('cpf')
            )

        elif tipo_doc == 'titulo_eleitor':
            if data.get('is_valid') is False or (data.get('is_valid') is None and data['document_type'] not in ('titulo_eleitor',)):
                return False
            return bool(
                data['fields'].get('nome_pessoa')
                and data['fields'].get('data_nascimento')
                and data['fields'].get('municipio')
                and data['fields'].get('estado')
                and data['fields'].get('zona')
                and data['fields'].get('secao')
                and data['fields'].get('data_emissao')
                and data['fields'].get('numero_titulo')
            )

        return False

    def insert_document_delivery(self, aluno, url_doc, curso_entrega, posicao, usuario,
                                  tipo_doc, api_resposta, is_valid, titular, base, tipo_extra=None):
        """Insere a entrega do documento no banco e dispara migração."""
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
        self.db_manager.execute_query(query_insert, [url_doc.replace(base, ""), url_doc])

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
        resultado_migracao = self.insert_validation_and_migration({
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
        """Insere validação do documento e executa migração de dados se válido."""
        result_insere = self.db_manager.insert_document_validation(
            id_doc=doc['id_doc'],
            aluno=doc['aluno'],
            tipo_documento=doc['tipo_doc'],
            response=doc['api_resposta'],
            valido='S' if doc['is_valid'] else 'N',
            titular=doc['titular']
        )

        migration_result = None
        result_visto = None

        if doc['is_valid']:
            tipo_migracao = doc['tipo_extra'] if doc['tipo_extra'] not in (None, '') else doc['tipo_doc']
            migration_result = self._execute_migration(tipo_migracao, doc['api_resposta'], doc['aluno'])

            result_update = self.db_manager.execute_query(
                STATUS_UPDATE_QUERY, ('Entregue', doc['aluno'], doc['tipo_doc'])
            )
            result_visto = self.confirm_visto_confere(aluno=doc['aluno'])
        else:
            result_update = self.db_manager.execute_query(
                STATUS_UPDATE_QUERY, ('Inválido', doc['aluno'], doc['tipo_doc'])
            )

        return {
            'insere_validacao': result_insere,
            'migracao_dados': migration_result,
            'atualizacao_status': result_update,
            'visto_confere': result_visto
        }

    def _execute_migration(self, tipo_doc: str, data: Dict[str, Any], aluno: str):
        """
        Executa a migração dos dados para o banco.

        Args:
            tipo_doc: Tipo do documento
            data: Dados extraídos
            aluno: Código do aluno

        Returns:
            True se migração executada, False se tipo não suportado, ou dict com erro
        """
        try:
            migration_class = self.migration_classes.get(tipo_doc)

            if not migration_class:
                logger.info(f"Tipo de documento não suportado para migração: {tipo_doc}")
                return False

            migration = migration_class(self.db_manager)
            rows_affected = migration.migrate(data, aluno)
            logger.info(f"Migração executada para {tipo_doc} - {rows_affected} linhas afetadas")
            return True

        except Exception as e:
            logger.error(f"Erro na migração para {tipo_doc}: {str(e)}")
            return 0

    def confirm_visto_confere(self, aluno):
        """Verifica se todos os documentos estão entregues e atualiza o Visto Confere."""
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

                att = self.db_manager.execute_query(sql, (aluno,))

                if att > 0:
                    return {"status": True}
                else:
                    return {"status": False, "Motivo": f"Não foi atualizado: {att}"}

            except Exception as e:
                return {"status": False, "Mensagem": f"Não foi possível atualizar o Visto Confere do aluno {aluno} por motivos {e}"}
        else:
            return {"status": True, "Mensagem": f"Nem todos os documentos estão entregues: {resultado}"}

    def process_pending_document(self, aluno, documento, curso_entrega, posicao, usuario):
        """Monta o dict de documento e delega para process_document."""
        doc = {
            'ALUNO': aluno,
            'DOC': documento,
            "curso_entrega": curso_entrega,
            "posicao": posicao,
            "usuario": usuario
        }
        return self.process_document(doc)


def main(payload):
    """Função principal simplificada."""
    from shared.config import DATABASE_CONFIG

    processor = DocumentProcessorWeb(DATABASE_CONFIG)

    try:
        result = processor.process_pending_document(
            aluno=payload['aluno'],
            documento=payload['arquivo'],
            curso_entrega=payload['curso_entrega'],
            usuario=payload['usuario'],
            posicao=payload['posicao']
        )
        return result

    except Exception as e:
        return {
            "status": "error",
            "mensagem": str(e)
        }
