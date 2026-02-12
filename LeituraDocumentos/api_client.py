#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cliente de API - Sistema de Processamento de Documentos
Gerencia comunicação com APIs externas
"""

import requests
import json
import time
from typing import Dict, Any, Optional
from urllib.parse import urljoin


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
            'X-API-Key': '11BtClxfG39xxbqCo07hN43Vz6vthzM47XJuQEZO'
        }
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                print(f"Tentativa {attempt + 1}/{self.max_retries + 1} para processar documento: {tipo_doc}")
                
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
                        print(f"Erro HTTP 504 (timeout) na tentativa {attempt + 1}. Aguardando {self.retry_delay}s antes de tentar novamente...")
                        time.sleep(self.retry_delay)
                        continue
                    
                    # Para outros erros HTTP ou se esgotaram as tentativas
                    raise Exception(f"Erro HTTP {response.status_code}: {error_message}")
                
                # Se chegou aqui, a requisição foi bem-sucedida
                print(f"Documento processado com sucesso na tentativa {attempt + 1}")
                return response.json()
                
            except requests.exceptions.Timeout as e:
                last_exception = e
                if attempt < self.max_retries:
                    print(f"Timeout na tentativa {attempt + 1}. Aguardando {self.retry_delay}s antes de tentar novamente...")
                    time.sleep(self.retry_delay)
                    continue
                else:
                    raise Exception(f"Timeout após {self.max_retries + 1} tentativas: {str(e)}")
                    
            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < self.max_retries:
                    print(f"Erro de requisição na tentativa {attempt + 1}: {str(e)}. Aguardando {self.retry_delay}s antes de tentar novamente...")
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
    
    def get_cep_data(self, cep: str) -> Dict[str, Any]:
        """
        Obtém dados de endereço via CEP usando a API ViaCEP
        
        Args:
            cep: CEP a ser consultado
            
        Returns:
            Dados do endereço
            
        Raises:
            Exception: Em caso de erro na consulta
        """
        # Remove caracteres não numéricos do CEP
        cep_clean = ''.join(filter(str.isdigit, cep))
        
        if len(cep_clean) != 8:
            raise Exception("CEP deve ter 8 dígitos")
        
        # Formata CEP com hífen
        cep_formatted = f"{cep_clean[:5]}-{cep_clean[5:]}"
        
        url = f"https://viacep.com.br/ws/{cep_formatted}/json/"
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code != 200:
                raise Exception(f"Erro ao consultar CEP: HTTP {response.status_code}")
            
            data = response.json()
            
            # Verifica se o CEP foi encontrado
            if 'erro' in data:
                raise Exception("CEP não encontrado")
            
            return data
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Erro ao consultar CEP: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"Erro ao decodificar resposta do CEP: {str(e)}")
    
    def get_city_code(self, cidade: str, estado: str) -> Optional[str]:
        """
        Obtém o código da cidade (implementação simplificada)
        Em um sistema real, isso seria uma consulta ao banco de dados
        
        Args:
            cidade: Nome da cidade
            estado: Sigla do estado
            
        Returns:
            Código da cidade ou None se não encontrado
        """
        # Esta é uma implementação simplificada
        # Em um sistema real, seria feita uma consulta ao banco de dados
        # para buscar o código da cidade baseado no nome e estado
        
        # Mapeamento simplificado para demonstração
        city_codes = {
            ('São Paulo', 'SP'): '00009295',
            ('Rio de Janeiro', 'RJ'): '00009296',
            ('Belo Horizonte', 'MG'): '00009297',
            # Adicione mais cidades conforme necessário
        }
        
        return city_codes.get((cidade, estado))
    
    def close(self):
        """
        Fecha a sessão HTTP
        """
        self.session.close()
    
    def __enter__(self):
        """
        Suporte para context manager
        """
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Suporte para context manager
        """
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
        """
        Fecha a sessão HTTP
        """
        self.session.close()
    
    def __enter__(self):
        """
        Suporte para context manager
        """
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Suporte para context manager
        """
        self.close()
