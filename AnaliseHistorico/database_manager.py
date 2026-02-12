"""
Gerenciador de Banco de Dados

Responsável por:
- Construção da string de conexão
- Gerenciamento de conexões com SQL Server
- Execução segura de queries
- Operações específicas do domínio de análise de histórico

Observação:
Este módulo abstrai o acesso ao banco para evitar lógica SQL espalhada
pela aplicação.
"""

import json
from typing import Dict, Any, List, Optional, Sequence
import pyodbc
from contextlib import contextmanager



class DatabaseManager:
    """
    Gerencia conexões e operações com SQL Server usando pyodbc.

    A classe centraliza:
    - Criação e fechamento de conexões
    - Commit / rollback
    - Padronização de retorno das operações
    """

    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa o gerenciador de banco de dados.

        Args:
            config: Dicionário com configurações de conexão.
                    Espera-se as chaves:
                    - host
                    - database
                    - user
                    - password
                    - port (opcional)
        """
        self.config = config
        self.connection_string = self._build_connection_string()

    
    def _build_connection_string(self) -> str:
        """
        Monta a string de conexão ODBC para SQL Server.

        A configuração utiliza:
        - Criptografia habilitada
        - TrustServerCertificate para ambientes controlados
        - Autenticação por usuário/senha (não integrada)

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
            "Trusted_Connection=no;"
        )

    
    @contextmanager
    def get_connection(self):
        """
        Context manager para controle do ciclo de vida da conexão.

        Garante:
        - rollback em caso de erro
        - fechamento da conexão sempre
        - isolamento de falhas de banco

        Yields:
            Conexão ativa com o banco de dados
        """
        connection = None
        try:
            connection = pyodbc.connect(self.connection_string)
            yield connection
        except Exception as e:
            # Em caso de erro, desfaz qualquer alteração pendente
            if connection:
                connection.rollback()
            raise e
        finally:
            # Garante liberação da conexão
            if connection:
                connection.close()

    
    def execute_query(self, query: str, params: Optional[Sequence[Any]] = None) -> int:
        """
        Executa uma query SQL que altera dados.

        Utilizar para:
        - UPDATE
        - DELETE
        - INSERT sem retorno de ID

        Args:
            query: SQL parametrizado
            params: Parâmetros posicionais da query

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

        
    def execute_insert_returning_id(self, query: str, params=None) -> int:
        """
        Executa um INSERT que retorna o ID gerado via OUTPUT INSERTED.ID.

        Uso esperado:
        - Criação de registros que serão atualizados posteriormente

        Returns:
            ID do registro inserido
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                inserted_id = cursor.fetchone()[0]
                conn.commit()
                return inserted_id
            except Exception as e:
                conn.rollback()
                raise e


    
    def fetch_one(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Executa uma query e retorna apenas um registro.

        Ideal para:
        - Consultas por ID
        - Validações pontuais

        Returns:
            Dicionário com os dados ou None
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
        Executa uma query e retorna todos os registros encontrados.

        Returns:
            Lista de dicionários representando as linhas retornadas
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

    def inserir_analise_historico(self, id_analise, usuario_id):
        """
        Cria um registro inicial de validação de dispensa.

        O registro começa:
        - ACEITO = 'N'
        - ATIVO = 1

        Returns:
            Status da operação e ID gerado
        """
        try:
            query = """
                INSERT INTO DTB_ANCHIETA_PROD.dbo.ANC_VALIDA_DISPENSA
                    (FK_ID_ANALISE, DT_VALIDACAO, USUARIO, ACEITO, ATIVO)
                OUTPUT INSERTED.ID
                VALUES (?, GETDATE(), ?, 'N', 1)
            """
            execucao = self.execute_insert_returning_id(query, (id_analise, usuario_id))

            return {
                "status": "sucesso",
                "mensagem": "Análise salva com sucesso",
                "buscaId": execucao
            }

        except Exception as e:
            return {
                "status": "erro",
                "mensagem": "Erro ao salvar análise no banco de dados",
                "detalhes": str(e)
            }

    def anular_validacao(self, id, erro):
        """
        Inativa uma análise e registra o motivo do erro.

        Usado quando:
        - Falha de processamento
        - Erro de integração
        """
        try:
            query = """
                UPDATE DTB_ANCHIETA_PROD.dbo.ANC_VALIDA_DISPENSA
                SET ATIVO = 0,
                    motivo_erro = ?
                WHERE ID = ?
            """
            params = (erro, id)
            execucao = self.execute_query(query, params)

            if execucao > 0:
                return {
                    "status": "sucesso",
                    "mensagem": "Análise anulada com sucesso"
                }
            else:
                return {
                    "status": "erro",
                    "mensagem": "Nenhuma linha foi afetada ao anular a análise",
                    "detalhes": str(execucao)
                }

        except Exception as e:
            return {
                "status": "erro",
                "mensagem": "Erro ao anular o processamento da análise no banco de dados",
                "detalhes": str(e)
            }

    def salvar_analise_historico(self, id, resultado: Dict[str, Any], grade):
        """
        Salva o resultado final da análise de histórico.

        Campos persistidos:
        - Grade atual
        - Grade cursada (extração)
        - Resultado da comparação

        Os dados são armazenados em JSON para rastreabilidade.
        """
        try:
            query = """
                UPDATE DTB_ANCHIETA_PROD.dbo.ANC_VALIDA_DISPENSA
                SET GRADE_ATUAL = ?, 
                    GRADE_CURSADA = ?, 
                    RESPOSTA_IA = ?
                WHERE ID = ?
            """

            params = (
                json.dumps(grade, ensure_ascii=False),
                json.dumps(resultado['extracao'], ensure_ascii=False),
                json.dumps(resultado['comparacao'], ensure_ascii=False),
                id
            )

            execucao = self.execute_query(query, params)

            if execucao > 0:
                return {
                    "status": "sucesso",
                    "mensagem": "Análise processada e salva com sucesso"
                }
            else:
                return {
                    "status": "erro",
                    "mensagem": "Nenhuma linha foi afetada ao salvar a análise",
                    "detalhes": str(execucao)
                }

        except Exception as e:
            return {
                "status": "erro",
                "mensagem": "Erro ao salvar o processamento da análise no banco de dados",
                "detalhes": str(e)
            }

        