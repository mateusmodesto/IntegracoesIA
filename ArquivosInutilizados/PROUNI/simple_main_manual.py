#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema Simplificado de Processamento de Documentos
Método main que busca documentos no banco, processa via API e atualiza dados
"""

import json
import time
from typing import Dict, Any, List
from .LerDocumentoClass import Gemini
from .database_manager import DatabaseManager
from shared.config import get_logger

logger = get_logger(__name__)


class DocumentProcessorWeb:
    def __init__(self, database_config: Dict[str, Any]):
        """
        Inicializa o processador
        
        Args:
            database_config: Configurações do banco de dados
        """
        self.db_manager = DatabaseManager(database_config)
        self.gemi = Gemini()
       


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
        tipo_doc = document['tipo_documento']

        base = "https://ged-anchieta.s3.amazonaws.com/"


        try:
            api_resposta = self.gemi.analisarDocumento(url=url_doc, tipo_doc=tipo_doc)

            if api_resposta.get('Erro'):
                return {
                    "status": "error",
                    'message': 'Erro ao se conectar com a IA',
                    'api_resposta': api_resposta
                }
            
            resposta = self.db_manager.update_documento_prouni(aluno=aluno, resposta_IA=api_resposta, tipo_doc=tipo_doc, url_doc=url_doc)

            return {"status": "sucesso", "banco": resposta, "api_resposta": api_resposta}
                
        except Exception as e:            
            # Verifica se é um erro de timeout ou 504
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
    

    def process_pending_document(self, aluno, documento, tipo_documento):
        doc = {'ALUNO': aluno, 'DOC': documento, "tipo_documento": tipo_documento}
        return self.process_document(doc)

class DocumentProcessorManual:
        def __init__(self, database_config: Dict[str, Any]):
            """
            Inicializa o processador
            
            Args:
                database_config: Configurações do banco de dados
            """
            self.db_manager = DatabaseManager(database_config)
            self.gemi = Gemini()


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
            url_doc = document['CAMINHO']
            tipo_doc = document['TIPO_DOCUMENTO']
            categoria = document['CATEGORIA']

            base = "https://ged-anchieta.s3.amazonaws.com/"

            logger.info("==="*30)
            logger.info(f"Processando documento do aluno: {aluno}, tipo: {tipo_doc}")
            logger.info("==="*30)
            try:
                api_resposta = self.gemi.analisarDocumento(url=url_doc, tipo_doc=tipo_doc)
                logger.info(api_resposta)
                if api_resposta.get('Erro'):
                    self.db_manager.update_documento_prouni(resposta_IA=api_resposta, dados=document)
                    return {
                        "status": "error",
                        'message': 'Erro ao se conectar com a IA',
                        'api_resposta': api_resposta
                    }
                
                resposta = self.db_manager.update_documento_prouni(resposta_IA=api_resposta, dados=document)
                return {"status": "sucesso", "banco": resposta, "api_resposta": api_resposta}
            
            except Exception as e:
                logger.error(f"Falha ao processar documento do aluno {aluno}, tipo {tipo_doc}: {e}")

                is_timeout_error = (
                    'timeout' in str(e).lower() or
                    '504' in str(e) or
                    'endpoint request timed out' in str(e).lower()
                )

                if is_timeout_error:
                    logger.info(f"Documento do aluno {aluno} teve timeout, precisa retry")
                    return {
                        'status': 'timeout',
                        'retry_needed': True
                    }

                return {
                    "status": "error",
                    'message': str(e),
                    'retry_needed': False
                }

        def process_manual(self):
            resultados = []
            erros = []
            arquivos = self.db_manager.buscar_documentos_pendentes()
            logger.info(f"Entrando no processo - {len(arquivos)} documentos pendentes")

            for i, arquivo in enumerate(arquivos, 1):
                resultado = self.process_document(arquivo)
                resultados.append(resultado)

                if resultado.get('status') in ('error', 'timeout'):
                    erros.append(resultado)
                time.sleep(2)
            total_erros = len(erros)
            total_sucesso = len(resultados) - total_erros

            logger.info(f"{'==='*30}")
            logger.info(f"Resultado final: {total_sucesso} sucesso, {total_erros} erros de {len(arquivos)} documentos")
            logger.info(f"{'==='*30}")

            if erros:
                logger.error("Resumo dos erros:")
                for j, erro in enumerate(erros, 1):
                    logger.error(f"  {j}. {erro.get('message', erro.get('status'))}")

            return {
                "status": "sucesso" if total_erros == 0 else "parcial",
                "message": f"{len(arquivos)} documentos processados ({total_sucesso} ok, {total_erros} erros)",
                "erros": erros
            }
        
        
        

def main_manual():
    """
    Função principal simplificada
    """
    from shared.config import DATABASE_CONFIG

    processor = DocumentProcessorManual(DATABASE_CONFIG)

    try:
        result = processor.process_manual()
        logger.info(f"{result}")
        return result

    except Exception as e:
        logger.error(f"ERRO FATAL: {e}")
        return {
            "status": "error",
            "mensagem": str(e)
        }

if __name__ == "__main__":
    main_manual()
