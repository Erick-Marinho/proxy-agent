from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from langchain_openai import ChatOpenAI
from app.application.tool import get_company_info, get_budget_info
from langchain_core.messages import BaseMessage
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
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
            state_modifier=(
                "Você é um especialista em informações corporativas. "
                "Chame get_company_info com a pergunta do usuário. Use a resposta da ferramenta. "
                "Não peça detalhes adicionais antes de consultar a ferramenta."
            ),
            name="company_specialist",
            prompt="""
            Você é um especialista em informações corporativas.
            Chame get_company_info com a pergunta do usuário. Use a resposta da ferramenta.
            Não peça detalhes adicionais antes de consultar a ferramenta.
            """

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
            name="budget_specialist",
            prompt="""
            Você é um especialista em orçamentos.
            Chame get_budget_info com a pergunta do usuário. Use a resposta da ferramenta.
            Não peça detalhes adicionais antes de consultar a ferramenta.
            """

        )

    def build(self):
        """
        Constrói o agente proxy supervisor
        """
        company_agent = self._create_company_agent()
        budget_agent = self._create_budget_agent()

        supervisor = create_supervisor(
            agents=[company_agent, budget_agent],
            model=self.model,
            name="supervisor",
            prompt=(
                "Você é um supervisor de agentes especializados. "
                "Roteia perguntas para agentes apropriados e fornece resposta final. "
                "Para perguntas sobre preços/orçamentos: use budget_specialist. "
                "Para perguntas sobre empresa/serviços: use company_specialist. "
                "Quando um agente retornar com informação de ferramenta, apenas remova prefixos técnicos e entregue a informação diretamente. "
                "Se a resposta contém preço específico (ex: R$ 80,00), use exatamente esse valor."
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



