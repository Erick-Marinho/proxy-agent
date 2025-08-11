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

# Função auxiliar simples para identificar o agente usado
def _identify_agent_used(messages: list, original_message: str) -> str:
    # Prioridade 1: ferramenta utilizada
    if any(getattr(m, "name", "") == "get_budget_info" for m in messages):
        return "budget_specialist"
    if any(getattr(m, "name", "") == "get_company_info" for m in messages):
        return "company_specialist"

    # Prioridade 2: último agente especializado que falou
    for m in reversed(messages):
        name = getattr(m, "name", None)
        if name in ("budget_specialist", "company_specialist"):
            return name

    # Checagem minimalista de erro para perguntas de preço
    lower = (original_message or "").lower()
    price_keywords = [
        "quanto custa", "preço", "valor", "orçamento", "cotação", "custa", "custo", "valores"
    ]
    if any(k in lower for k in price_keywords):
        return "supervisor_error"

    return "supervisor"

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
        
        # Extrai resposta final e agente usado de forma simples
        messages = result.get("messages", [])
        last_message = messages[-1]
        response_text = last_message.content
        agent_used = _identify_agent_used(messages, request.message)
        
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
