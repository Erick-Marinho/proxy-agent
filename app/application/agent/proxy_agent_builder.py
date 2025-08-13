from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from langchain_openai import ChatOpenAI
from app.application.tool import get_company_info, get_budget_info
from langchain_core.messages import BaseMessage
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
import logging
import os

from app.application.tool.handle_customer_agent_tool import handle_customer_data

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
            state_modifier=(
                "Você é um especialista em informações corporativas. "
                "Chame get_company_info com a pergunta do usuário. Use a resposta da ferramenta. "
                "Não peça detalhes adicionais antes de consultar a ferramenta."
            ),
            name="company_specialist"
        )

    def _create_budget_agent(self):
        budget_model = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0
        )
        return create_react_agent(
            model=budget_model,
            tools=[get_budget_info],
            state_modifier="Chame get_budget_info com a pergunta do usuário. Use a resposta da ferramenta.",
            name="budget_specialist"
        )
    
    def _create_handle_customer_data_agent(self):
        return create_react_agent(
            model=self.model,
            tools=[handle_customer_data],
            state_modifier=(
                "Chame get_customer_data quando o usuário fornecer dados pessoais como:"
                "- nome, CPF, Email, Endereço, Cidade, Estado, CEP."
                "Use a resposta da ferramenta para coletar os dados do usuário."
            ),
            name="colect_customer_data_specialist"
        )

    def build(self):
        """
        Constrói o agente proxy supervisor
        """
        company_agent = self._create_company_agent()
        budget_agent = self._create_budget_agent()
        handle_customer_data_agent = self._create_handle_customer_data_agent()

        supervisor = create_supervisor(
            agents=[company_agent, budget_agent, handle_customer_data_agent],
            model=self.model,
            name="supervisor",
            prompt=(
                "Você é um supervisor de agentes especializados. "
                "Roteia perguntas para agentes apropriados e fornece a resposta final diretamente ao usuário. "
                "Para perguntas sobre preços/orçamentos: use budget_specialist. "
                "Para perguntas sobre empresa/serviços: use company_specialist. "
                "Para perguntas sobre dados do cliente: use colect_customer_data_specialist. "
                "Ao entregar a resposta final: nunca mencione qual agente ou ferramenta foi usada; não use metacomunicação ou bastidores; "
                "não escreva frases como 'o agente de orçamento forneceu...' ou 'o agente da empresa informou...'. "
                "Quando um agente retornar com informação de ferramenta, remova prefixos técnicos (como 'Informações de Orçamento:' ou 'Informações da Empresa:') e entregue a informação diretamente. "
                "Se a resposta contiver valores/preços específicos (ex: R$ 80,00), preserve-os exatamente. "
                "Se houver estrutura em lista vinda da informação, preserve-a; caso contrário, responda de forma breve e direta."
            )
        )

        logger.info("Agente proxy supervisor construído com sucesso")

        return supervisor

    def compile(self):
        """
        Compila o grafo de estado do agente proxy supervisor
        """

        compile_supervisor = self.build().compile()
        logger.info("Agente proxy supervisor compilado com sucesso")
        return compile_supervisor



def get_proxy_agent():
    """
    Exporta o grafo compilado esperado pelo runtime (conforme langgraph.json).
    """
    return ProxyAgentBuilder().compile()



