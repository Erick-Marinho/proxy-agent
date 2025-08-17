import logging
import httpx
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

@tool
async def get_budget_info(query: str) -> str:
    """
    Consulta informações sobre orçamentos, cotações e precificação.
    Use esta ferramenta para perguntas sobre orçamento.
    """
    logger.info(f"Consultando agente de orçamentos: {query}")

    enforced_query = (
        "INSTRUÇÕES: Responda com orçamento EXATO, sem intervalos. "
        "Se houver quantidade, informe preço unitário e TOTAL. "
        "Preserve números e formato (R$ 0,00). Não use prefixos técnicos. "
        "RETORNE apenas o conteúdo final ao cliente.\n\n"
        f"CONSULTA: {query}"
    )


    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://budget-agent.livelygrass-5e1cbc66.brazilsouth.azurecontainerapps.io/chat",
                json={"message": enforced_query},
                timeout=30.0,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()

                # Extrai a resposta dependendo da estrutura retornada
                if isinstance(result, dict):
                    budget_response = (
                        result.get("response")
                        or result.get("message")
                        or result.get("answer")
                        or str(result)
                    )
                else:
                    budget_response = str(result)

                logger.info("Resposta recebida do agente de orçamentos")
                return budget_response
            else:
                logger.error(f"Erro HTTP {response.status_code}: {response.text}")
                return f"Erro ao consultar dados de orçamento. Status: {response.status_code}"

        except httpx.TimeoutException:
            logger.error("Timeout ao chamar agente de orçamentos")
            return "Timeout: O agente de orçamentos demorou para responder."

        except httpx.ConnectError:
            logger.error("Erro de conexão ao chamar agente de orçamentos")
            return "Erro de conexão: Não foi possível conectar ao agente de orçamentos."

        except Exception as e:
            logger.error(f"Erro ao consultar agente de orçamentos: {e}")
            return f"Erro inesperado ao consultar dados de orçamento: {str(e)}"
