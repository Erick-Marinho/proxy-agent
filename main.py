import logging
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from app.application.agent.proxy_agent_builder import ProxyAgentBuilder
from langchain_core.messages import HumanMessage
import uvicorn
from app.presentation.proxy_router import router as proxy_router

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


app.include_router(proxy_router, prefix="/proxy", tags=["proxy"])


@app.get("/", summary="Root endpoint", description="Root endpoint for the API")
async def root():
    return {
        "message": "Proxy Agent Supervisor is running",
        "endpoints": {
            "POST /proxy/chat": "Chat com o agente supervisor",
        },
        "status": "success",
        "version": "1.1.0",
        "docs": "http://localhost:8000/docs",        
    }

@app.get("/health")
async def health_check():
    """
    Endpoint de health check
    """
    return {"status": "healthy", "service": "proxy-agent-supervisor"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
