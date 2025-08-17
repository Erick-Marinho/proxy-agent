from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from langchain_openai import ChatOpenAI
from app.application.tool import get_company_info, get_budget_info, handle_customer_data
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
                    "Chame get_customer_data quando o usuário fornecer dados pessoais como "
                    "nome, CPF, Email, Endereço, Cidade, Estado, CEP. "
                    "Use a resposta da ferramenta para coletar os dados do usuário."
                )
            ),
            name="colect_customer_data_specialist",
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
                "Adote a persona 'Yasmin - Doutor Sofá'. "
                "Na primeira resposta, cumprimente e pergunte qual item deseja higienizar (sem pedir foto). "
                "Após o usuário informar o item (e quantidade se presente), consulte company_specialist "
                "para entregar a explicação do serviço. Em seguida, consulte budget_specialist e EXIJA "
                "preço unitário e TOTAL exatos (sem intervalos), preservando números e formato. "
                "Remova qualquer prefixo técnico de ferramentas. Depois pergunte se há mais itens. "
                "Não mencione agentes/ferramentas."
            )
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



