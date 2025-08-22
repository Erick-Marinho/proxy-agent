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
                    "Não peça detalhes adicionais antes de consultar a ferramenta."
                    "Informe como funciona a higienização preferencialmente"
                )
            ),
            name="company_specialist",
        )

    def _create_budget_agent(self):
        return create_react_agent(
            model=self.model,
            tools=[get_budget_info] ,
            prompt=SystemMessage(
                content=(
                    "Chame get_budget_info com a pergunta do usuário. "
                    "Use a resposta da ferramenta."
                    "O pagamento sempre deve ser via PIX ou em 2x no crédito"
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
                    "Chame get_service_and_budget_info com a descrição do item. "
                    "Ao chamar a ferramenta, inclua na 'query' um resumo curto da intenção "
                    "atual do cliente inferida do histórico recente (item específico e "
                    "quantidade quando existirem). "
                    "Responda EXATAMENTE com o conteúdo retornado pela ferramenta; "
                    "não reescreva, não resuma, não acrescente texto próprio. "
                    "Se nesta conversa já houver explicação recente sobre 'como funciona', "
                    "a ferramenta pode retornar apenas o orçamento e CTA."
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
                "(ex.: 'Oi, eu sou a Yasmin, da Doutor Sofá') e pergunte o item a higienizar. "
                "2) Para pedidos de preço/orçamento/cotação, PREFIRA delegar ao "
                "'service_and_budget_specialist' para combinar explicação + orçamento. "
                "Evite usar o 'budget_specialist' diretamente, salvo exceções. "
                "2.1) Se o especialista retornar múltiplas opções (ex.: 'Variações disponíveis:' "
                "ou perguntar 'qual opção específica?' ou solicitação de item/quantidade), "
                "OBRIGATORIAMENTE REPASSE A MENSAGEM COMPLETA, incluindo TODAS as variações de preços "
                "e TODAS as informações. NÃO DELEGUE para coleta. Apenas REPASSE EXATAMENTE "
                "TODA a resposta do especialista ao usuário e AGUARDE a resposta do cliente. "
                "2.2) Após o USUÁRIO informar explicitamente o item e, se houver, a quantidade, "
                "delegue NOVAMENTE ao 'service_and_budget_specialist' com essa especificação "
                "para RETORNAR a explicação de 'como funciona' + o orçamento da opção escolhida. "
                "2.3) Depois de REPASSAR essa resposta ao usuário, NÃO pergunte dia/horário; "
                "delegue imediatamente ao 'colect_customer_data_specialist' para iniciar a coleta de dados. "
                "3) Se o usuário quiser prosseguir após receber APENAS o orçamento (sem a explicação), "
                "delegue ao 'service_and_budget_specialist' para incluir a explicação e, em seguida, "
                "delegue ao 'colect_customer_data_specialist'. "
                "4) REGRA CRÍTICA: Ao retornar de QUALQUER especialista, SEMPRE REPASSE "
                "INTEGRALMENTE TODO o texto retornado, palavra por palavra, PRESERVANDO "
                "TODAS as quebras de linha, TODOS os preços, TODAS as opções. "
                "NUNCA acrescente, remova, edite ou resuma NADA. "
                "5) Quando o cliente concordar/prosseguir OU fornecer dados pessoais, delegue ao "
                "'colect_customer_data_specialist'. Após a resposta, REPASSE EXATAMENTE o texto retornado. "
                "6) Se o especialista de coleta pedir apenas CONFIRMAÇÃO dos dados e o usuário confirmar "
                "(ex.: 'confirmo', 'ok', 'está correto'), então NÃO delegue novamente. "
                "Responda em UMA única linha: 'Perfeito! Um atendente dará sequência ao seu atendimento "
                "em instantes.' E nada mais. "
                "7) Nunca mencione agentes ou ferramentas internas. "
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



