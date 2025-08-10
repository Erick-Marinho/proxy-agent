import httpx
from langchain_core.tools import tool
import logging

logger = logging.getLogger(__name__)

@tool
async def get_company_info(query: str) -> str:
    """
    Consulta informações sobre a empresa, serviços oferecidos, produtos, 
    ou qualquer pergunta relacionada aos dados corporativos.
    Use esta ferramenta para perguntas sobre a empresa.
    """
    logger.info(f"Consultando agente da empresa: {query}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://conversation-agent.livelygrass-5e1cbc66.brazilsouth.azurecontainerapps.io/api/gateway",
                json={"message": query},
                timeout=30.0,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Extrai a resposta dependendo da estrutura retornada
                if isinstance(result, dict):
                    # Tenta diferentes campos possíveis de resposta
                    company_response = (
                        result.get("response") or 
                        result.get("message") or 
                        result.get("answer") or 
                        str(result)
                    )
                else:
                    company_response = str(result)
                
                logger.info(f"Resposta recebida do agente da empresa")
                return f"Informações da Empresa: {company_response}"
            else:
                logger.error(f"Erro HTTP {response.status_code}: {response.text}")
                return f"Erro ao consultar dados da empresa. Status: {response.status_code}"
                
        except httpx.TimeoutException:
            logger.error("Timeout ao chamar agente da empresa")
            return "Timeout: O agente da empresa demorou para responder."
            
        except httpx.ConnectError:
            logger.error("Erro de conexão ao chamar agente da empresa")
            return "Erro de conexão: Não foi possível conectar ao agente da empresa."
            
        except Exception as e:
            logger.error(f"Erro ao consultar agente da empresa: {e}")
            return f"Erro inesperado ao consultar dados da empresa: {str(e)}"

