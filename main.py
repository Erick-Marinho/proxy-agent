import logging
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from app.application.agent.proxy_agent_builder import ProxyAgentBuilder
from langchain_core.messages import HumanMessage
import uvicorn

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",    
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Proxy Agent", 
    description="Proxy Agent Supervisor for company information orchestration",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Remove a inicialização global
# proxy_supervisor = ProxyAgentBuilder().compile()

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    agent_used: str

@app.get("/", summary="Root endpoint", description="Root endpoint for the API")
async def root():
    return {
        "message": "Proxy Agent Supervisor is running",
        "status": "success",
        "version": "0.1.0",
        "docs": "http://localhost:8000/docs",        
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Endpoint para conversar com o proxy agent supervisor
    """
    try:
        logger.info(f"Pergunta recebida: {request.message}")
        
        # Cria supervisor a cada requisição (evita cache)
        proxy_supervisor = ProxyAgentBuilder().compile()
        
        # Cria estado inicial
        initial_state = {"messages": [HumanMessage(content=request.message)]}
        
        # Executa o supervisor
        result = await proxy_supervisor.ainvoke(initial_state)
        
        logger.info(f"Resultado completo: {result}")
        
        # Extrai resposta
        last_message = result["messages"][-1]
        response_text = last_message.content
        
        # Verifica tool calls na mensagem
        tool_calls = getattr(last_message, 'tool_calls', [])
        logger.info(f"Tool calls detectadas: {tool_calls}")
        
        # Determina qual agente foi usado baseado nas tool calls
        original_message = request.message.lower()
        price_keywords = ["quanto custa", "preço", "valor", "orçamento", "cotação", "custa", "custo", "valores"]
        has_price_keyword = any(keyword in original_message for keyword in price_keywords)
        
        logger.info(f"Pergunta original: {original_message}")
        logger.info(f"Contém palavra-chave de preço: {has_price_keyword}")
        
        # Lógica melhorada para detecção do agente usado
        if tool_calls:
            # Se há tool calls, analisa qual ferramenta foi chamada
            tool_names = [call.get('name', '') for call in tool_calls]
            if any('transfer_to_budget_specialist' in str(tool) for tool in tool_names):
                agent_used = "budget_specialist"
            elif any('transfer_to_company_specialist' in str(tool) for tool in tool_names):
                agent_used = "company_specialist"
            else:
                agent_used = "supervisor"
        else:
            # Se não há tool calls, verifica se deveria haver
            if has_price_keyword:
                logger.warning("AVISO: Pergunta sobre preço não gerou tool call para budget_specialist")
                agent_used = "supervisor_error"  # Indica erro de roteamento
            else:
                agent_used = "supervisor"
        
        # Verifica se há conteúdo específico na resposta
        response_content = response_text.lower()
        if "informações de orçamento" in response_content:
            agent_used = "budget_specialist"
        elif "informações da empresa" in response_content:
            agent_used = "company_specialist"
        
        logger.info(f"Requisição processada - Agente usado: {agent_used}")
        
        return ChatResponse(
            response=response_text,
            agent_used=agent_used
        )
        
    except Exception as e:
        logger.error(f"Erro no chat: {e}")
        return ChatResponse(
            response="Desculpe, ocorreu um erro interno.",
            agent_used="error"
        )

@app.get("/health")
async def health_check():
    """
    Endpoint de health check
    """
    return {"status": "healthy", "service": "proxy-agent-supervisor"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
