from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from langchain_openai import ChatOpenAI
from app.application.tool import get_company_info
import logging
import os

logger = logging.getLogger(__name__)

class ProxyAgentBuilder:
    """
    Classe responsável por construir o agente proxy supervisor
    """

    def __init__(self):
        """
        Inicializa o construtor do agente proxy
        """
        self.model = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY")
        )

    def _create_company_agent(self):
        """
        Cria o agente especializado em dados da empresa
        """
        return create_react_agent(
            model=self.model,
            tools=[get_company_info],
            state_modifier=(
                "Você é um especialista em informações corporativas. "
                "Use a ferramenta get_company_info para consultar dados sobre a empresa, "
                "serviços oferecidos, produtos, ou qualquer informação corporativa. "
                "Seja prestativo e forneça respostas completas baseadas nas informações recebidas."
            ),
            name="company_agent"
        )

    def build(self):
        """
        Constrói o supervisor e seus agentes especializados
        """
        # Cria os agentes especializados
        company_agent = self._create_company_agent()
        
        # Cria o supervisor
        supervisor = create_supervisor(
            agents=[company_agent],
            model=self.model,
            state_modifier=(
                "Você é um supervisor proxy inteligente. "
                "Analise as solicitações dos usuários e delegue para o agente apropriado. "
                "Para perguntas sobre a empresa, serviços, produtos ou dados corporativos, "
                "use o company_agent. "
                "Para conversas gerais ou cumprimentos, responda diretamente de forma prestativa."
            )
        )
        
        logger.info("Supervisor proxy construído com sucesso")
        return supervisor

    def compile(self):
        """
        Compila o agente proxy supervisor
        """
        compiled_supervisor = self.build().compile()
        logger.info("Supervisor proxy compilado com sucesso")
        return compiled_supervisor

# Função para o LangGraph Dev Server
def get_proxy_agent():
    """
    Função factory para o LangGraph dev server
    Retorna o agente proxy compilado
    """
    builder = ProxyAgentBuilder()
    return builder.compile()