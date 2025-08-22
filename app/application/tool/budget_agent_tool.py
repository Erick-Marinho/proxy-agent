import httpx
from langchain_core.tools import tool

@tool
async def get_budget_info(query: str) -> str:
    """
    Query the external budget agent with the user message and return its raw text.
    """
    url = "https://budget-agent.livelygrass-5e1cbc66.brazilsouth.azurecontainerapps.io/chat"
    payload = {"message": (query or "").strip()}
    headers = {"Content-Type": "application/json"}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=30.0, headers=headers)
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, dict):
                    return (
                        result.get("response")
                        or result.get("message")
                        or result.get("answer")
                        or str(result)
                    )
                return str(result)
            return f"Erro ao consultar dados de orçamento. Status: {response.status_code}"
        except httpx.TimeoutException:
            return "Timeout: O agente de orçamentos demorou para responder."
        except httpx.ConnectError:
            return "Erro de conexão: Não foi possível conectar ao agente de orçamentos."
        except Exception as e:
            return f"Erro inesperado ao consultar dados de orçamento: {str(e)}"