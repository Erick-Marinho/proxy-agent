import asyncio
import logging
from langchain_core.tools import tool

from app.application.tool.budget_agent_tool import get_budget_info
from app.application.tool.company_agent_tool import get_company_info

logger = logging.getLogger(__name__)

def _preview(value: object, limit: int = 800) -> str:
    try:
        s = str(value) if value is not None else ""
    except Exception as e:
        s = f"<unrenderable: {e}>"
    if len(s) > limit:
        return s[:limit] + "...(truncated)"
    return s

@tool
async def get_service_and_budget_info(query: str) -> str:
    """
    Versão mínima para depuração:
    - Chama em paralelo o agente de orçamento e o agente de 'como funciona'.
    - Loga payloads e retornos (preview).
    - Retorna a concatenação: <company_info> + duas quebras + <budget_info>.
    """
    sanitized_query = (query or "").strip()
    logger.info("[service_budget:min] query=%r", sanitized_query)

    # Payloads
    payload_budget = {"query": sanitized_query}
    company_info_query = (
        "Forneça uma explicação COMPLETA e DETALHADA sobre como funciona a "
        "higienização da Doutor Sofá. Inclua: produtos (ANVISA), estabilizador "
        "de pH, método semi-seco (extração até ~5cm), benefícios (extração "
        "industrial, odores, secagem 8-12h, serviço no local), observações "
        "(não garantir remoção total de manchas, não expor ao sol, não usar panos, "
        "prazo 48h para reparos/retorno) e garantia (renovação do estofado). "
        "Não inclua preços nem CTA."
    )
    payload_company = {"query": company_info_query}

    logger.info("[service_budget:min] budget payload=%r", payload_budget)
    logger.info("[service_budget:min] company payload=%r", payload_company)

    # Chamadas em paralelo
    budget_task = get_budget_info.ainvoke(payload_budget)
    company_task = get_company_info.ainvoke(payload_company)

    logger.info("[service_budget:min] aguardando respostas em paralelo...")
    company_info, budget_info = await asyncio.gather(
        company_task, budget_task, return_exceptions=True
    )

    # Logs dos retornos
    if isinstance(company_info, Exception):
        logger.warning("[service_budget:min] company_info ERROR: %s", company_info)
        company_text = ""
    else:
        logger.info(
            "[service_budget:min] company_info ok: type=%s len=%s",
            type(company_info).__name__, len(str(company_info))
        )
        logger.debug("[service_budget:min] company_info preview:\n%s", _preview(company_info))
        company_text = str(company_info).strip()

    if isinstance(budget_info, Exception):
        logger.warning("[service_budget:min] budget_info ERROR: %s", budget_info)
        budget_text = ""
    else:
        logger.info(
            "[service_budget:min] budget_info ok: type=%s len=%s",
            type(budget_info).__name__, len(str(budget_info))
        )
        logger.debug("[service_budget:min] budget_info preview:\n%s", _preview(budget_info))
        budget_text = str(budget_info).strip()

    parts: list[str] = []
    if company_text:
        parts.append(company_text)
    if budget_text:
        parts.append(budget_text)

    final_text = "\n\n".join(parts) if parts else "Não foi possível obter informações no momento."
    logger.info("[service_budget:min] RESPOSTA FINAL ENVIADA AO USUÁRIO:\n%s", final_text)
    logger.debug("[service_budget:min] final preview:\n%s", _preview(final_text))
    return final_text
