from . import LerHistorico as lerHistorico
from . import database_manager as db_manager


class AnaliseHistorico:
    """
    Classe orquestradora do processo de análise de histórico escolar.

    Papel desta classe:
    - Coordenar banco de dados, IA e validações
    - Controlar o ciclo de vida da análise (criação, processamento, persistência ou anulação)
    - Garantir consistência em caso de falha em qualquer etapa

    Importante:
    Nenhuma regra pesada de equivalência vive aqui.
    A comparação é responsabilidade exclusiva da IA.
    """

    def __init__(self, payload):
        """
        Inicializa a análise com os dados vindos da API.

        payload esperado:
        {
            'id_analise': int,
            'usuario_id': int,
            'historico': str | None,            # URL de PDF / imagem / zip
            'historico_interno': dict | None,   # Histórico já estruturado
            'grade': str,                       # Currículo
            'candidato': int
        }
        """
        # Cliente responsável por comunicação com a IA
        self.gemini = lerHistorico.Gemini()

        # Gerenciador centralizado de banco de dados
        # Mantém conexão, commit, rollback e padronização de retorno
        self.db = db_manager.DatabaseManager({
            'host': '192.168.0.9',
            'database': 'dtb_lyceum_prod',
            'user': 'lyceum',
            'password': 'lyceum',
            'port': 1433
        })

        # Payload original recebido da API (não modificar)
        self.payload = payload


    def processar_historico(self, grade):
        """
        Executa o fluxo completo de análise do histórico.

        Etapas:
        1) Cria registro inicial no banco
        2) Decide qual tipo de histórico será usado
        3) Chama IA para extração/comparação
        4) Valida retornos
        5) Persiste resultado ou anula análise

        Parâmetros:
        - grade (dict): grade curricular normalizada

        Retorno:
        - dict com status, mensagem e detalhes
        """

        # Cria o registro inicial da análise no banco
        # Esse ID será usado para UPDATE ou anulação
        id = self.db.inserir_analise_historico(
            self.payload['id_analise'],
            self.payload['usuario_id']
        )

        # Validação defensiva:
        # Se falhar aqui, nada deve continuar
        if not id or not isinstance(id, dict) or 'buscaId' not in id:
            return {
                "status": "erro",
                "mensagem": "Falha ao iniciar análise no banco de dados",
                "detalhes": "inserir_analise_historico retornou valor inválido"
            }


        try:
            """
            Regra de decisão da fonte de dados:

            - Apenas histórico externo:
              → PDF / imagem / ZIP

            - Apenas histórico interno:
              → JSON estruturado já validado

            - Ambos:
              → IA usa os dois, priorizando o interno
            """

            if self.payload['historico_interno'] is None:
                # Caso comum: histórico enviado como arquivo
                resultado = self.gemini.transformToJson(
                    url=self.payload['historico'],
                    grade=grade
                )

            elif self.payload['historico'] is None:
                # Caso em que só existe histórico interno
                try:
                    comparacao = self.gemini.send_for_docling(
                        docling_doc=None,
                        historico_interno=self.payload['historico_interno'],
                        grade=grade
                    )

                    # Padroniza saída para manter contrato com o restante do sistema
                    resultado = {
                        "extracao": self.payload['historico_interno'],
                        "comparacao": comparacao
                    }

                except Exception as e:
                    # Qualquer erro aqui invalida a análise
                    self.db.anular_validacao(id['buscaId'], e)
                    return {
                        "status": "erro",
                        "mensagem": "Erro ao analisar histórico interno",
                        "detalhes": str(e)
                    }

            else:
                # Cenário completo: histórico externo + interno
                resultado = self.gemini.transformToJson(
                    url=self.payload['historico'],
                    historico_interno=self.payload['historico_interno'],
                    grade=grade
                )
            
            # Segurança básica:
            # IA obrigatoriamente deve retornar um dicionário
            if not isinstance(resultado, dict):
                self.db.anular_validacao(
                    id['buscaId'],
                    f"Resultado inválido retornado pela IA: {resultado}"
                )
                return {
                    "status": "erro",
                    "mensagem": "Resposta inválida do serviço de IA",
                    "detalhes": resultado
                }

            # Erro explícito retornado pela IA
            if (
                resultado.get("Erro") is True
                or (isinstance(resultado.get("extracao"), dict) and resultado["extracao"].get("Erro"))
                or (isinstance(resultado.get("comparacao"), dict) and resultado["comparacao"].get("Erro"))
            ):
                self.db.anular_validacao(id['buscaId'], resultado)
                return {
                    "status": "erro",
                    "mensagem": "Erro ao analisar o histórico",
                    "detalhes": resultado
                }


            # A comparação deve gerar uma lista de disciplinas equivalentes
            if 'comparacao_disciplinas' not in resultado['comparacao']:
                self.db.anular_validacao(
                    id['buscaId'],
                    f"Nenhuma equivalência encontrada: {resultado}"
                )
                return {
                    "status": "erro",
                    "mensagem": "Não há comparacao do histórico ou estrutura inválida",
                    "detalhes": resultado
                }

            elif resultado['comparacao']['comparacao_disciplinas'] == []:
                self.db.anular_validacao(
                    id['buscaId'],
                    f"Nenhuma equivalência encontrada: {resultado}"
                )
                return {
                    "status": "erro",
                    "mensagem": "Não há comparacao do histórico",
                    "detalhes": resultado
                }

            # Persistência da análise
            try:
                execucao = self.db.salvar_analise_historico(
                    id['buscaId'],
                    resultado,
                    grade
                )

                if execucao['status'] == 'sucesso':
                    return {
                        "status": "sucesso",
                        "mensagem": "Análise processada e salva com sucesso",
                        "detalhes": resultado
                    }

                # Falha ao salvar no banco
                self.db.anular_validacao(
                    id['buscaId'],
                    "Erro ao salvar análise no banco de dados"
                )
                return {
                    "status": "erro",
                    "mensagem": "Erro ao salvar análise no banco de dados",
                    "detalhes": execucao
                }

            except Exception as e:
                self.db.anular_validacao(id['buscaId'], resultado)
                return {
                    "status": "erro",
                    "mensagem": "Erro ao tentar salvar análise no banco de dados",
                    "detalhes": str(e)
                }

        except Exception as e:
            # Erro inesperado no fluxo principal
            self.db.anular_validacao(
                id['buscaId'],
                f"Erro ao começar o processo de comparar: {e}"
            )


        except Exception as e:
            
            self.db.anular_validacao(
                id['buscaId'],
                f"Erro ao começar o processo de comparar: {e}"
            )

        
    def buscarGrade(self):
        """
        Busca a grade curricular do aluno no banco e normaliza os dados.

        Retorno:
        - dict com chave sendo o nome da disciplina em UPPER
        - Estrutura otimizada para comparação textual pela IA
        """

        resultado = self.db.fetch_all(
            """
            SELECT
                ID, ID_CANDIDATO, CURRICULO, SERIE,
                COD_DISCIPLINA, DISCIPLINA, CH,
                NOTA_EXT, DISCIPLINA_EXT,
                DISPENSA, DEPENDENCIA, ADAPTACAO,
                REGULAR, ANO, SEMESTRE
            FROM dtb_anchieta_prod.dbo.ANC_TRANSF_ANALISE_ALUNO
            WHERE CURRICULO = ?
              AND ID_CANDIDATO = TRY_CAST(? AS INT)
            """,
            [self.payload['grade'], self.payload['candidato']]
        )

        json_novas = {}

        for item in resultado:
            nome = item.get("DISCIPLINA")
            if not nome:
                continue

            # Normalização para comparação textual
            chave = nome.strip().upper()

            json_novas[chave] = {
                "codigo": item.get("COD_DISCIPLINA"),
                "carga_horaria": item.get("CH"),
                "semestre": item.get("SEMESTRE"),
                "serie": item.get("SERIE"),
                "regular": item.get("REGULAR"),
                "dependencia": item.get("DEPENDENCIA"),
                "dispensa": item.get("DISPENSA"),
            }

        return json_novas



def main(payload):
    """
    Ponto de entrada padrão do módulo.

    Fluxo:
    - Instancia AnaliseHistorico
    - Busca grade curricular
    - Processa o histórico completo

    Retorna diretamente o JSON final para a API.
    """
    analise = AnaliseHistorico(payload)
    grade = analise.buscarGrade()
    return analise.processar_historico(grade)

