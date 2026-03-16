#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilitários - Sistema de Processamento de Documentos
Funções auxiliares para formatação e conversão de dados
"""

import re
from datetime import datetime
from typing import Optional, Tuple, Dict, Any


class Utils:
    """
    Classe com funções utilitárias para formatação e conversão de dados
    """
    
    # Mapeamento de estados brasileiros
    ESTADOS_BRASIL = {
        'Acre': 'AC', 'Alagoas': 'AL', 'Amapá': 'AP', 'Amazonas': 'AM', 'Bahia': 'BA',
        'Ceará': 'CE', 'Distrito Federal': 'DF', 'Espírito Santo': 'ES', 'Goiás': 'GO',
        'Maranhão': 'MA', 'Mato Grosso': 'MT', 'Mato Grosso do Sul': 'MS', 'Minas Gerais': 'MG',
        'Pará': 'PA', 'Paraíba': 'PB', 'Paraná': 'PR', 'Pernambuco': 'PE', 'Piauí': 'PI',
        'Rio de Janeiro': 'RJ', 'Rio Grande do Norte': 'RN', 'Rio Grande do Sul': 'RS',
        'Rondônia': 'RO', 'Roraima': 'RR', 'Santa Catarina': 'SC', 'São Paulo': 'SP',
        'Sergipe': 'SE', 'Tocantins': 'TO'
    }
    
    def __init__(self):
        """Inicializa a classe de utilitários"""
        pass
    
    def clean_document_number(self, document: str) -> str:
        """
        Remove caracteres não numéricos de um número de documento
        
        Args:
            document: Número do documento
            
        Returns:
            Número limpo (apenas dígitos)
        """
        if not document:
            return ''
        return re.sub(r'[^\d]', '', str(document))
    
    def format_cpf(self, cpf: str) -> str:
        """
        Formata CPF no padrão XXX.XXX.XXX-XX
        
        Args:
            cpf: CPF sem formatação
            
        Returns:
            CPF formatado
        """
        cpf_clean = self.clean_document_number(cpf)
        
        if len(cpf_clean) != 11:
            return cpf_clean
        
        return f"{cpf_clean[:3]}.{cpf_clean[3:6]}.{cpf_clean[6:9]}-{cpf_clean[9:]}"
    
    def format_cep(self, cep: str) -> str:
        """
        Formata CEP no padrão XXXXX-XXX
        
        Args:
            cep: CEP sem formatação
            
        Returns:
            CEP formatado
        """
        cep_clean = self.clean_document_number(cep)
        
        if len(cep_clean) != 8:
            return cep_clean
        
        return f"{cep_clean[:5]}-{cep_clean[5:]}"
    
    def parse_date_br(self, date_str: str) -> Optional[datetime]:
        """
        Converte string de data no formato brasileiro (dd/MM/yyyy) para datetime
        
        Args:
            date_str: String da data no formato dd/MM/yyyy
            
        Returns:
            Objeto datetime ou None se inválido
        """
        if not date_str:
            return None
        
        try:
            # Remove espaços extras
            date_str = date_str.strip()
            
            # Tenta diferentes formatos de data
            formats = [
                '%d/%m/%Y',
                '%d-%m-%Y',
                '%d.%m.%Y',
                '%Y-%m-%d',
                '%d/%m/%y',
                '%d-%m-%y'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            return None
            
        except Exception:
            return None
    
    def format_date_sql(self, date_obj: datetime) -> str:
        """
        Formata data para uso em SQL Server
        
        Args:
            date_obj: Objeto datetime
            
        Returns:
            String formatada para SQL Server
        """
        if not date_obj:
            return 'NULL'
        
        return date_obj.strftime('%Y-%m-%d')
    
    def parse_local_nascimento(self, local_nascimento: str) -> Tuple[str, str]:
        """
        Extrai cidade e estado do local de nascimento
        
        Args:
            local_nascimento: String com local de nascimento
            
        Returns:
            Tupla com (cidade, estado)
        """
        if not local_nascimento:
            return '', ''

        # Divide cidade e estado pelo separador de vírgula
        partes = [parte.strip() for parte in local_nascimento.split(',')]

        cidade = partes[0] if len(partes) > 0 else ''
        estado = partes[1] if len(partes) > 1 else ''

        # Remove prefixo "Estado de " se existir
        estado = re.sub(r'^(Estado\s+de\s+)', '', estado, flags=re.IGNORECASE).strip()

        # Converter sigla (se for o caso, sua função já cuida disso)
        if estado:
            estado = self.convert_estado_sigla(estado)

        return cidade, estado
    
    def convert_estado_sigla(self, estado: str) -> str:
        """
        Converte nome do estado para sigla
        
        Args:
            estado: Nome ou sigla do estado
            
        Returns:
            Sigla do estado
        """
        if not estado:
            return ''
        
        estado_clean = estado.strip()
        
        # Se já é uma sigla válida (2 letras maiúsculas)
        if re.match(r'^[A-Z]{2}$', estado_clean):
            return estado_clean
        
        # Se é um nome completo, converte para sigla
        if estado_clean in self.ESTADOS_BRASIL:
            return self.ESTADOS_BRASIL[estado_clean]
        
        # Tenta extrair sigla do final do estado
        match = re.search(r'([A-Z]{2})$', estado_clean)
        if match:
            return match.group(1)
        
        return estado_clean
    
    def extract_address_number(self, endereco: str) -> str:
        """
        Extrai número do endereço
        
        Args:
            endereco: String com endereço completo
            
        Returns:
            Número extraído do endereço
        """
        if not endereco:
            return ''
        
        # Expressão regular para capturar o número após o nome da rua
        patterns = [
            r'(?:[^\d]+)[\s\.,\-\/]+(\d{1,6})\b',  # Número após separadores
            r'\b(\d{1,6})\b'  # Primeiro número isolado
        ]
        
        for pattern in patterns:
            match = re.search(pattern, endereco)
            if match:
                return match.group(1)
        
        return ''
    
    def format_name_initcap(self, nome: str) -> str:
        """
        Formata nome com iniciais maiúsculas (equivalente ao InitCap do SQL Server)
        
        Args:
            nome: Nome a ser formatado
            
        Returns:
            Nome formatado
        """
        if not nome:
            return ''
        
        # Divide o nome em palavras
        palavras = nome.split()
        
        # Formata cada palavra
        palavras_formatadas = []
        for palavra in palavras:
            if palavra:
                # Primeira letra maiúscula, resto minúsculo
                palavra_formatada = palavra[0].upper() + palavra[1:].lower()
                palavras_formatadas.append(palavra_formatada)
        
        return ' '.join(palavras_formatadas)
    
    def compare_first_names(self, nome_atual: str, nome_novo: str) -> bool:
        """
        Compara se os primeiros nomes são iguais
        
        Args:
            nome_atual: Nome atual
            nome_novo: Nome novo
            
        Returns:
            True se os primeiros nomes são iguais
        """
        if not nome_atual or not nome_novo:
            return False
        
        primeiro_atual = nome_atual.split()[0] if nome_atual.split() else ''
        primeiro_novo = nome_novo.split()[0] if nome_novo.split() else ''
        
        return primeiro_atual.lower() == primeiro_novo.lower()
    
    def choose_name(self, nome_atual: str, nome_novo: str) -> str:
        """
        Escolhe qual nome usar baseado na comparação dos primeiros nomes
        
        Args:
            nome_atual: Nome atual no sistema
            nome_novo: Nome extraído do documento
            
        Returns:
            Nome escolhido
        """
        if not nome_atual:
            return nome_novo or ''
        
        if not nome_novo:
            return nome_atual
        
        # Se os nomes são idênticos, usa o novo
        if nome_atual.upper() == nome_novo.upper():
            return nome_novo
        
        # Se os primeiros nomes são iguais, usa o novo
        if self.compare_first_names(nome_atual, nome_novo):
            return nome_novo
        
        # Caso contrário, muda para o novo
        return nome_novo
    
    def validate_cpf(self, cpf: str) -> bool:
        """
        Valida CPF usando algoritmo oficial
        
        Args:
            cpf: CPF a ser validado
            
        Returns:
            True se o CPF é válido
        """
        cpf_clean = self.clean_document_number(cpf)
        
        if len(cpf_clean) != 11:
            return False
        
        # Verifica se todos os dígitos são iguais
        if cpf_clean == cpf_clean[0] * 11:
            return False
        
        # Calcula primeiro dígito verificador
        soma = 0
        for i in range(9):
            soma += int(cpf_clean[i]) * (10 - i)
        
        resto = soma % 11
        digito1 = 0 if resto < 2 else 11 - resto
        
        if int(cpf_clean[9]) != digito1:
            return False
        
        # Calcula segundo dígito verificador
        soma = 0
        for i in range(10):
            soma += int(cpf_clean[i]) * (11 - i)
        
        resto = soma % 11
        digito2 = 0 if resto < 2 else 11 - resto
        
        return int(cpf_clean[10]) == digito2
    
    def clean_text(self, text: str) -> str:
        """
        Limpa texto removendo caracteres especiais e normalizando espaços
        
        Args:
            text: Texto a ser limpo
            
        Returns:
            Texto limpo
        """
        if not text:
            return ''
        
        # Remove caracteres de controle e normaliza espaços
        text = re.sub(r'\s+', ' ', text.strip())
        
        return text
    
    def extract_phone_number(self, phone: str) -> str:
        """
        Extrai apenas números de um telefone
        
        Args:
            phone: String com telefone
            
        Returns:
            Apenas os números do telefone
        """
        if not phone:
            return ''
        
        return self.clean_document_number(phone)
    
    def format_phone(self, phone: str) -> str:
        """
        Formata telefone no padrão brasileiro
        
        Args:
            phone: Telefone sem formatação
            
        Returns:
            Telefone formatado
        """
        phone_clean = self.extract_phone_number(phone)
        
        if len(phone_clean) == 10:  # Telefone fixo
            return f"({phone_clean[:2]}) {phone_clean[2:6]}-{phone_clean[6:]}"
        elif len(phone_clean) == 11:  # Celular
            return f"({phone_clean[:2]}) {phone_clean[2:7]}-{phone_clean[7:]}"
        
        return phone_clean
