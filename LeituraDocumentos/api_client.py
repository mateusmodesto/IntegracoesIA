#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cliente de API - Sistema de Processamento de Documentos
Gerencia comunicação com APIs externas
"""

import json
import time
from typing import Dict, Any, Optional

import requests

from shared.config import AWS_API_KEY


class APIClient:
    """
    Classe para comunicação com APIs externas
    """
    
    def __init__(self, timeout: int = 30, max_retries: int = 3, retry_delay: int = 5):
        """
        Inicializa o cliente de API
        
        Args:
            timeout: Timeout para requisições em segundos
            max_retries: Número máximo de tentativas para requisições que falharam
            retry_delay: Delay entre tentativas em segundos
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session = requests.Session()
        
        # Headers padrão
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'DocumentProcessor/1.0'
        })
    
    def get_docs_data(self, url: str, tipo_doc: str) -> Dict[str, Any]:
        """
        Obtém dados de um documento via API de processamento com retry automático
        
        Args:
            url: URL do documento
            tipo_doc: Tipo do documento
            
        Returns:
            Dados extraídos do documento
            
        Raises:
            Exception: Em caso de erro na requisição após todas as tentativas
        """
        api_url = "https://tin3b8vg72.execute-api.sa-east-1.amazonaws.com/Prod/ler-processar-arquivos"
        
        payload = {
            "tipo_documento": tipo_doc,
            "url": url
        }
        
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': AWS_API_KEY
        }
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.post(
                    api_url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )
                
                # Verifica se houve erro HTTP
                if response.status_code >= 400:
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get('message', f'HTTP {response.status_code}')
                    
                    # Se for erro 504 (timeout) e ainda temos tentativas, tenta novamente
                    if response.status_code == 504 and attempt < self.max_retries:
                        time.sleep(self.retry_delay)
                        continue
                    
                    # Para outros erros HTTP ou se esgotaram as tentativas
                    raise Exception(f"Erro HTTP {response.status_code}: {error_message}")
                
                # Se chegou aqui, a requisição foi bem-sucedida
                return response.json()
                
            except requests.exceptions.Timeout as e:
                last_exception = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    raise Exception(f"Timeout após {self.max_retries + 1} tentativas: {str(e)}")
                    
            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    raise Exception(f"Erro na requisição após {self.max_retries + 1} tentativas: {str(e)}")
                    
            except json.JSONDecodeError as e:
                # Erro de JSON não deve ser retentado
                raise Exception(f"Erro ao decodificar resposta JSON: {str(e)}")
        
        # Se chegou aqui, todas as tentativas falharam
        if last_exception:
            raise Exception(f"Falha após {self.max_retries + 1} tentativas. Último erro: {str(last_exception)}")
        else:
            raise Exception("Falha inesperada após múltiplas tentativas")
    
    def close(self):
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class ViaCEPClient:
    """
    Cliente específico para a API ViaCEP
    """
    
    def __init__(self, timeout: int = 10):
        """
        Inicializa o cliente ViaCEP
        
        Args:
            timeout: Timeout para requisições em segundos
        """
        self.timeout = timeout
        self.base_url = "https://viacep.com.br/ws"
        self.session = requests.Session()
    
    def consultar_cep(self, cep: str) -> Dict[str, Any]:
        """
        Consulta dados de endereço por CEP
        
        Args:
            cep: CEP a ser consultado (com ou sem formatação)
            
        Returns:
            Dados do endereço
            
        Raises:
            ValueError: Se o CEP for inválido
            Exception: Em caso de erro na consulta
        """
        # Limpa o CEP
        cep_clean = ''.join(filter(str.isdigit, cep))
        
        if len(cep_clean) != 8:
            raise ValueError("CEP deve ter 8 dígitos")
        
        # Formata o CEP
        cep_formatted = f"{cep_clean[:5]}-{cep_clean[5:]}"
        
        url = f"{self.base_url}/{cep_formatted}/json/"
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if 'erro' in data:
                raise Exception("CEP não encontrado")
            
            return data
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Erro ao consultar CEP: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"Erro ao decodificar resposta: {str(e)}")
    
    def close(self):
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
