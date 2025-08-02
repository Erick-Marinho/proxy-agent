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

# Inicializa o proxy agent supervisor
proxy_supervisor = ProxyAgentBuilder().compile()

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
        # Cria estado inicial
        initial_state = {"messages": [HumanMessage(content=request.message)]}
        
        # Executa o supervisor
        result = await proxy_supervisor.ainvoke(initial_state)
        
        # Extrai resposta
        last_message = result["messages"][-1]
        response_text = last_message.content
        
        # Determina qual agente foi usado
        agent_used = "company_agent" if "get_company_info" in str(result.get("tool_calls", [])) else "supervisor"
        
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
