import asyncio
import logging
import re
from langchain_core.tools import tool

from app.application.tool.budget_agent_tool import get_budget_info
from app.application.tool.company_agent_tool import get_company_info

logger = logging.getLogger(__name__)

def _has_multiple_options(text: str) -> bool:
    """Verifica se o texto contém múltiplas opções de orçamento"""
    patterns = [
        r"Variaç(ões|oes)\s+dispon[ií]veis",
        r"Para seguirmos, qual opção específica",
    ]
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True
    return False

def _is_user_confirming_choice(query: str) -> bool:
    """
    Verifica se o usuário está confirmando/escolhendo uma opção específica
    ao invés de fazer uma consulta genérica inicial
    """
    # Indicadores de confirmação/escolha
    confirmation_indicators = [
        r"\bquero\b",
        r"\bescolho\b", 
        r"\bvou\s+de\b",
        r"\bprefiro\b",
        r"\besse\b",
        r"\bessa\b",
        r"\bsim\b",
        r"\bok\b",
        # Especificações diretas de tipo/quantidade
        r"\b\d+\s+lugares?\b",
        r"\b(um|uma|dois|duas|três|quatro|cinco)\s+lugares?\b",
        r"\bretrátil\b",
        r"\bcanto\b",
        r"\bchaise\b",
        r"\breclinável\b",
        r"\bpoltrona\b",
        r"\bcolchão\b",
        r"\bcadeira\b",
    ]
    
    logger.info(f"Verificando se '{query}' é confirmação/escolha...")
    
    for pattern in confirmation_indicators:
        if re.search(pattern, query, flags=re.IGNORECASE):
            logger.info(f"Indicador de escolha '{pattern}' encontrado - INCLUIR HIGIENIZAÇÃO")
            return True
    
    logger.info(f"Nenhum indicador de escolha encontrado - CONSULTA GENÉRICA")
    return False

@tool
async def get_service_and_budget_info(query: str) -> str:
    """
    Retorna orçamento do budget_agent e, quando apropriado, explicação de higienização.
    """
    logger.info(f"Iniciando consulta para: {query}")

    # Verifica se é confirmação/escolha específica
    should_include_hygiene_info = _is_user_confirming_choice(query)
    logger.info(f"Incluir info de higienização? {should_include_hygiene_info}")
    
    # Sempre busca o orçamento (dados reais da API) - CORRIGIDO: passando query diretamente
    budget_info_task = get_budget_info.ainvoke(query)
    
    # Só busca informações de higienização se for escolha específica
    if should_include_hygiene_info:
        logger.info("Buscando informações de higienização")
        company_info_query = (
            "Forneça uma explicação COMPLETA e DETALHADA sobre como funciona a higienização da Doutor Sofá. "
            "OBRIGATÓRIO incluir TODOS os seguintes pontos em detalhes:\n\n"
            "1. PRODUTOS: Produtos homologados pela ANVISA com efeito bactericida, antiácaros, antimicrobiano e fungicida\n"
            "2. ESTABILIZADOR: Estabilizador de pH que neutraliza agentes tensoativos e reduz desgaste do tecido\n"
            "3. MÉTODO: Lavagem semi-seca que extrai sujidades até 5cm abaixo da superfície\n"
            "4. BENEFÍCIOS: Liste com bullets:\n"
            "   - Higienização de alta qualidade com extração industrial\n"
            "   - Eliminação de odores (suor, mofo, vômito)\n"
            "   - Secagem rápida (8-12 horas)\n"
            "   - Serviço no endereço do cliente (45min-1h)\n"
            "5. OBSERVAÇÕES IMPORTANTES:\n"
            "   - Não prometemos remoção de todas as manchas\n"
            "   - Não expor ao sol após higienização\n"
            "   - Não usar panos sobre o estofado\n"
            "   - Reparos em até 48h\n"
            "   - Retorno se necessário em até 48h\n"
            "6. GARANTIA: Limpeza e higienização - estofado renovado na aparência, toque e frescor\n\n"
            "Use parágrafos organizados e bullets detalhados. Seja completo e informativo. "
            "NÃO inclua preços, formas de pagamento ou CTA de agendamento."
        )
        company_info_task = get_company_info.ainvoke(company_info_query)
        results = await asyncio.gather(company_info_task, budget_info_task, return_exceptions=True)
        company_info = results[0] if not isinstance(results[0], Exception) else None
        budget_info = results[1] if not isinstance(results[1], Exception) else f"Erro: {results[1]}"
        logger.info(f"Company info obtida: {len(company_info) if company_info else 0} caracteres")
    else:
        logger.info("Consultando apenas orçamento")
        budget_info = await budget_info_task
        if isinstance(budget_info, Exception):
            budget_info = f"Erro: {budget_info}"
        company_info = None

    # Monta a resposta
    if should_include_hygiene_info and company_info:
        # Escolha específica: informações de higienização + orçamento real da API
        logger.info("Resposta com higienização + orçamento")
        formatted_response = f"{company_info}\n\n{budget_info}"
    else:
        # Consulta genérica: apenas orçamento real da API (com múltiplas opções)
        logger.info("Resposta apenas com orçamento")
        formatted_response = budget_info

    logger.info(f"Resposta final: {len(formatted_response)} caracteres")
    return formatted_response
