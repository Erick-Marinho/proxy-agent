import httpx
from langchain_core.tools import tool

import logging
logger = logging.getLogger(__name__)

def _format_currency_br(value: object) -> str:
    try:
        num = float(value)
    except Exception:
        return str(value)
    s = f"{num:,.2f}"
    # Converte para padrão brasileiro (ponto milhar, vírgula decimal)
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

def _format_services(services: list[dict]) -> str:
    lines: list[str] = []
    for item in services or []:
        name = (
            item.get("servico_nome")
            or item.get("name")
            or item.get("servico")
            or "Serviço"
        )
        price = item.get("valor") or item.get("price") or item.get("preco")
        price_txt = _format_currency_br(price) if price is not None else "-"
        lines.append(f"- {name}: R$ {price_txt}")
    return "\n".join(lines)

def _compose_budget_text(result: dict | object) -> str:
    if not isinstance(result, dict):
        return str(result)

    header = (
        result.get("response")
        or result.get("message")
        or result.get("answer")
        or ""
    )
    services = result.get("services") or []
    qty = result.get("quantity")

    services_txt = _format_services(services) if services else ""
    parts: list[str] = []
    if header:
        parts.append(str(header).strip())
    if services_txt:
        parts.append(services_txt)
    # Opcional: se houver apenas serviços sem header, mantemos só a lista
    final_text = "\n".join(parts).strip() or str(result)

    # Caso a API informe quantidade e não haja header explícito, não adicionamos
    # rótulos extras para cumprir a regra de não inventar texto.
    return final_text

@tool
async def get_budget_info(query: str) -> str:
    """
    Acessa o agente de orçamentos para obter informações sobre o orçamento.
    """
    url = "https://budget-agent.livelygrass-5e1cbc66.brazilsouth.azurecontainerapps.io/chat"
    payload = {"message": (query or "").strip()}
    headers = {"Content-Type": "application/json"}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=30.0, headers=headers)
            result = response.json() if response.status_code == 200 else None
            logger.info(f"Resposta do agente de orçamentos: {result}")
            if response.status_code == 200:
                return _compose_budget_text(result)
            return f"Erro ao consultar dados de orçamento. Status: {response.status_code}"
        except httpx.TimeoutException:
            return "Timeout: O agente de orçamentos demorou para responder."
        except httpx.ConnectError:
            return "Erro de conexão: Não foi possível conectar ao agente de orçamentos."
        except Exception as e:
            return f"Erro inesperado ao consultar dados de orçamento: {str(e)}"
