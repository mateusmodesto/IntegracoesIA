#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema Simplificado de Processamento de Documentos
Método main que busca documentos no banco, processa via API e atualiza dados
"""

import json
from typing import Dict, Any, List
from .LerDocumentoClass import Gemini
from .database_manager import DatabaseManager


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
    

    def process_pending_document(self, aluno, documento, tipo_documento):
        doc = {'ALUNO': aluno, 'DOC': documento, "tipo_documento": tipo_documento}
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
                tipo_documento=payload['tipo_documento'])
    
        return result
    
    except Exception as e:
        
        return {
            "status": "error",
            "mensagem": str(e)
        }