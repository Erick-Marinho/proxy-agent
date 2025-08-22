from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from langchain_openai import ChatOpenAI
from app.application.tool import get_company_info, get_budget_info, handle_customer_data, get_service_and_budget_info
from langchain_core.messages import BaseMessage, SystemMessage
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from langgraph.types import Checkpointer
from langgraph.store.base import BaseStore
import logging
import os


logger = logging.getLogger(__name__)

class ProxyAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    next: str

class ProxyAgentBuilder:
    """
    Classe responsável por construir o agente proxy supervisor
    """

    def __init__(self):
        self.model = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0
        )

    def _create_company_agent(self):
        return create_react_agent(
            model=self.model,
            tools=[get_company_info],
            prompt=SystemMessage(
                content=(
                    "Você é um especialista em informações corporativas. "
                    "Chame get_company_info com a pergunta do usuário. Use a resposta da ferramenta. "
                    "Não peça detalhes adicionais antes de consultar a ferramenta. "
                    "Informe como funciona a higienização preferencialmente."
                )
            ),
            name="company_specialist",
        )

    def _create_budget_agent(self):
        return create_react_agent(
            model=self.model,
            tools=[get_budget_info],
            prompt=SystemMessage(
                content=(
                    "Você é o especialista de ORÇAMENTOS.\n"
                    "- SEMPRE chame get_budget_info PRIMEIRO com a mensagem original do usuário.\n"
                    "- Depois da ferramenta responder, sua MENSAGEM FINAL deve ser "
                    "EXATAMENTE o TEXTO retornado pela ferramenta.\n"
                    "- PROIBIDO adicionar qualquer palavra extra (ex.: 'O agente de orçamento forneceu...'), "
                    "comentários, resumos ou títulos. Preserve as QUEBRAS DE LINHA.\n"
                    "- Se a ferramenta retornar erro/timeout, devolva exatamente o texto retornado pela ferramenta.\n"
                    "- Se a ferramenta retornar vazio/incompleto, chame get_budget_info novamente uma vez.\n"
                )
            ),
            name="budget_specialist",
        )
    
    def _create_handle_customer_data_agent(self):
        return create_react_agent(
            model=self.model,
            tools=[handle_customer_data],
            prompt=SystemMessage(
                content=(
                    "Você coleta dados do cliente. "
                    "Agregue os dados já informados na conversa (Nome, Email, CPF, CEP, Número, Complemento) "
                    "e chame handle_customer_data apenas quando houver DADO NOVO do cliente. "
                    "Se a ferramenta solicitar campos faltantes, REPASSE essa solicitação em tom cordial, "
                    "listando TODOS os faltantes de uma só vez (bullets curtos), sem pedir um a um em turnos diferentes. "
                    "Não reenvie a mesma solicitação no mesmo turno e aguarde a resposta do usuário. "
                    "Responda sempre EXATAMENTE com o texto da ferramenta; não reescreva."
                )
            ),
            name="colect_customer_data_specialist",
        )

    def _create_service_and_budget_agent(self):
        return create_react_agent(
            model=self.model,
            tools=[get_service_and_budget_info],
            prompt=SystemMessage(
                content=(
                    "Você combina informações de serviço e orçamento. "
                    "Use esta ferramenta quando precisar apresentar VARIAÇÕES de itens "
                    "e/ou incluir a explicação de 'como funciona' junto do orçamento. "
                    "NÃO utilize esta ferramenta para perguntas EXCLUSIVAMENTE de preço/orçamento; "
                    "nesses casos o supervisor delegará ao 'budget_specialist'. "
                    "Ao chamar a ferramenta, inclua na 'query' um resumo curto da intenção "
                    "atual do cliente inferida do histórico recente (item específico e "
                    "quantidade quando existirem). "
                    "Responda EXATAMENTE com o conteúdo retornado pela ferramenta; "
                    "não reescreva, não resuma, não acrescente texto próprio. "
                    "Se nesta conversa já houver explicação recente sobre 'como funciona', "
                    "a ferramenta pode retornar apenas o orçamento."
                )
            ),
            name="service_and_budget_specialist",
        )

    def build(self):
        """
        Constrói o agente proxy supervisor
        """
        company_agent = self._create_company_agent()
        budget_agent = self._create_budget_agent()
        handle_customer_data_agent = self._create_handle_customer_data_agent()
        service_and_budget_agent = self._create_service_and_budget_agent()

        supervisor = create_supervisor(
            agents=[company_agent, budget_agent, handle_customer_data_agent, service_and_budget_agent],
            model=self.model,
            name="supervisor",
            prompt=(
                "Você é 'Yasmin - Doutor Sofá'. "
                "1) Primeiro contato: cumprimente brevemente e APRESENTE-SE como Yasmin "
                "(ex.: 'Oi, eu sou a Yasmin, da Doutor Sofá') e pergunte em que posso ajudar. "
                "2) Se o usuário PEDIR PREÇO/ORÇAMENTO/COTAÇÃO (ex.: 'qual o valor', 'quanto custa', 'orçamento'), "
                "DELEGUE ao 'budget_specialist'. "
                "2.1) Se for necessário apresentar VARIAÇÕES de itens e/ou combinar a explicação de "
                "'como funciona' com o orçamento, DELEGUE ao 'service_and_budget_specialist'. "
                "2.2) Se o 'service_and_budget_specialist' retornar múltiplas opções (ex.: 'Variações disponíveis:' "
                "ou fizer uma pergunta do tipo 'qual opção específica?'), REPASSE EXATAMENTE esse texto ao usuário "
                "e AGUARDE a resposta do cliente com o item/quantidade. "
                "2.3) Após o USUÁRIO informar explicitamente o item e, se houver, a quantidade, "
                "delegue NOVAMENTE ao 'service_and_budget_specialist' para RETORNAR a explicação de "
                "'como funciona' + o orçamento da opção escolhida. "
                "2.4) Depois de REPASSAR essa resposta ao usuário, NÃO pergunte dia/horário; "
                "delegue imediatamente ao 'colect_customer_data_specialist' para iniciar a coleta de dados. "
                "3) Ao retornar de QUALQUER especialista, REPASSE EXATAMENTE o texto retornado, "
                "caractere por caractere, PRESERVANDO QUEBRAS DE LINHA. "
                "NUNCA acrescente CTA, saudações, títulos, contexto ou qualquer frase adicional. "
                "Não reescreva, não resuma, não edite. "
                "4) Quando o cliente concordar/prosseguir OU fornecer dados pessoais, delegue ao "
                "'colect_customer_data_specialist'. Após a resposta, REPASSE EXATAMENTE o texto retornado. "
                "5) Se o especialista de coleta pedir apenas CONFIRMAÇÃO dos dados e o usuário confirmar "
                "(ex.: 'confirmo', 'ok', 'está correto'), então NÃO delegue novamente. "
                "Responda em UMA única linha: 'Perfeito! Um atendente dará sequência ao seu atendimento "
                "em instantes.' E nada mais. "
                "6) Nunca mencione agentes ou ferramentas internas. "
                "IMPORTANTE: Você NUNCA deve resumir, simplificar ou omitir informações dos especialistas."
            ),
        )

        logger.info("Agente proxy supervisor construído com sucesso")

        return supervisor

    def compile(self, checkpointer: Checkpointer | None = None, store: BaseStore | None = None):
        """
        Compila o grafo de estado do agente proxy supervisor
        """
        graph = self.build()
        compile_supervisor = graph.compile(checkpointer=checkpointer, store=store)
        logger.info("Agente proxy supervisor compilado com sucesso")
        return compile_supervisor



def get_proxy_agent():
    """
    Exporta o grafo compilado esperado pelo runtime (conforme langgraph.json).
    """
    return ProxyAgentBuilder().compile()
