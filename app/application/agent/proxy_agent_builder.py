from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from app.application.tool import get_company_info, get_budget_info
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from typing import TypedDict, Annotated, Literal
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
                "Use a ferramenta get_company_info para consultar dados sobre a empresa, "
                "serviços, produtos e informações institucionais. "
                "Sempre que receber uma pergunta, primeiro decida SE deve chamar a ferramenta; "
                "se sim, chame-a; somente depois sintetize a resposta."
            ),
            name="company_specialist"
        )

    def _create_budget_agent(self):
        return create_react_agent(
            model=self.model,
            tools=[get_budget_info],
            state_modifier=(
                "Você é um especialista em orçamentos e precificação de serviços de limpeza. "
                "REGRA INVIOLÁVEL: sua PRIMEIRA AÇÃO deve ser chamar a ferramenta "
                "get_budget_info passando a mensagem ORIGINAL do usuário como entrada. "
                "NUNCA forneça valores genéricos; SEMPRE use o retorno da ferramenta. "
                "Se a ferramenta falhar, explique o erro e peça reformulação."
            ),
            name="budget_specialist"
        )

    def _supervisor_node(self, state: ProxyAgentState):
        """
        Nó supervisor que decide para qual agente rotear
        """
        last_message = state["messages"][-1]
        content = last_message.content.lower()
        
        # Keywords de preço
        price_keywords = ["quanto custa", "preço", "valor", "orçamento", "custo", "cotação", "valores"]
        
        logger.info(f"Supervisor analisando: {content}")
        
        # Decide roteamento
        if any(keyword in content for keyword in price_keywords):
            logger.info("Roteando para budget_specialist")
            return {"next": "budget_specialist"}
        else:
            logger.info("Roteando para company_specialist")
            return {"next": "company_specialist"}

    def _router(self, state: ProxyAgentState) -> Literal["budget_specialist", "company_specialist", "__end__"]:
        """
        Função de roteamento baseada no estado
        """
        return state.get("next", "__end__")

    def build(self):
        # Cria os agentes
        company_agent = self._create_company_agent()
        budget_agent = self._create_budget_agent()
        
        # Cria o graph
        workflow = StateGraph(ProxyAgentState)
        
        # Adiciona nós
        workflow.add_node("supervisor", self._supervisor_node)
        workflow.add_node("budget_specialist", budget_agent)
        workflow.add_node("company_specialist", company_agent)
        
        # Define edges
        workflow.set_entry_point("supervisor")
        workflow.add_conditional_edges(
            "supervisor",
            self._router,
            {
                "budget_specialist": "budget_specialist",
                "company_specialist": "company_specialist"
            }
        )
        workflow.add_edge("budget_specialist", END)
        workflow.add_edge("company_specialist", END)
        
        logger.info("Supervisor proxy customizado construído com sucesso")
        return workflow

    def compile(self):
        compiled_supervisor = self.build().compile()
        logger.info("Supervisor proxy customizado compilado com sucesso")
        return compiled_supervisor

def get_proxy_agent():
    builder = ProxyAgentBuilder()
    return builder.compile()
