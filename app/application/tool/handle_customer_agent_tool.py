import logging
import httpx
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
async def handle_customer_data(query: str) -> str:
    """
    Coleta dados do cliente como: nome, CPF, Email, CEP,
    complemento e numero. Use esta ferramenta para coletar dados do cliente.
    """
    logger.info(f"Dados do cliente: {query}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://customer-registration-agent.livelygrass-5e1cbc66.brazilsouth.azurecontainerapps.io/coleta/chat",
                json={"message": query},
                timeout=30.0,
                headers={"Content-Type": "application/json"}
            )

            # Log da resposta
            logger.info(f"Status da resposta: {response.status_code}")
            logger.info(f"Conteúdo da resposta: {response.text}")
            
            if response.status_code == 200:
                result = response.json()

                # Log do resultado processado
                logger.info(f"Resultado processado: {result}")
                
                if isinstance(result, dict):
                    data = result.get("data", {}) or {}
                    cliente = data.get("cliente", {}) or {}
                    endereco = data.get("endereco", {}) or {}

                    # Texto do agente externo (quando disponível), para preservar o tom humanizado
                    agent_text = (
                        result.get("response")
                        or result.get("message")
                        or result.get("answer")
                        or ""
                    )

                    # Checagem de obrigatórios
                    obrigatorios = [
                        "nome_completo",
                        "email",
                        "cpf",
                        "cep",
                        "numero",
                        "complemento",
                    ]
                    faltantes = [c for c in obrigatorios if not cliente.get(c)]

                    nomes = {
                        "nome_completo": "Nome completo",
                        "email": "Email",
                        "cpf": "CPF",
                        "cep": "CEP",
                        "numero": "Número",
                        "complemento": "Complemento",
                    }

                    # Se houver faltantes: priorize o texto do agente externo; senão, peça de forma cordial
                    if faltantes:
                        if agent_text.strip():
                            return agent_text.strip()
                        faltantes_bullets = "\n".join(f"- {nomes.get(f, f)}" for f in faltantes)
                        return (
                            "Perfeito! Vamos precisar de alguns dados:\n"
                            f"{faltantes_bullets}\n\n"
                            "Pode me informar, por favor?"
                        )

                    # Todos obrigatórios presentes: incluir endereço completo e pedir confirmação
                    rua = endereco.get("rua")
                    bairro = endereco.get("bairro")
                    cidade = endereco.get("cidade")
                    estado = endereco.get("estado")
                    endereco_linha = ", ".join([p for p in [rua, bairro, cidade, estado] if p]) or None

                    resumo_bullets = (
                        f"- Nome: {cliente.get('nome_completo', 'N/A')}\n"
                        f"- Email: {cliente.get('email', 'N/A')}\n"
                        f"- CPF: {cliente.get('cpf', 'N/A')}\n"
                        f"- CEP: {cliente.get('cep', 'N/A')}\n"
                        f"- Número: {cliente.get('numero', 'N/A')}\n"
                        f"- Complemento: {cliente.get('complemento', 'N/A')}"
                        + (f"\n- Endereço: {endereco_linha}" if endereco_linha else "")
                    )

                    confirmacao_msg = "Consegue me confirmar se está tudo certinho? Se sim, eu sigo com o agendamento."

                    # Filtra o agent_text para remover mensagens de início inadequadas
                    filtered_agent_text = ""
                    if agent_text.strip():
                        # Remove frases típicas de início de cadastro quando já temos dados
                        filtered_text = agent_text.strip()
                        unwanted_phrases = [
                            "Olá! Para começarmos o seu cadastro",
                            "preciso que você me informe o seu nome completo, e-mail e CPF",
                            "Assim que tivermos essas informações, poderemos avançar",
                            "Agradeço pela sua colaboração!"
                        ]
                        
                        # Se o texto contém frases de início, não usar
                        contains_unwanted = any(phrase.lower() in filtered_text.lower() for phrase in unwanted_phrases)
                        if not contains_unwanted:
                            filtered_agent_text = filtered_text

                    partes = []
                    if filtered_agent_text:
                        partes.append(filtered_agent_text)
                    if endereco_linha:
                        partes.append(f"Endereço encontrado pelo CEP:\n{endereco_linha}")
                    partes.append("Por favor, confirme os dados para o agendamento:\n\n" + resumo_bullets)
                    partes.append(confirmacao_msg)

                    return "\n\n".join(partes)

                # Fallback se não vier dict
                return str(result)
                    
            else:
                logger.error(f"Erro HTTP {response.status_code}: {response.text}")
                return f"Erro ao consultar dados do cliente. Status: {response.status_code}"
                
        except httpx.TimeoutException:
            logger.error("Timeout ao chamar agente do cliente")
            return "Timeout: O agente do cliente demorou para responder."
            
        except httpx.ConnectError:
            logger.error("Erro de conexão ao chamar agente do cliente")
            return "Erro de conexão: Não foi possível conectar ao agente do cliente."
            
        except Exception as e:
            logger.error(f"Erro ao consultar agente do cliente: {e}")
            return f"Erro inesperado ao consultar dados do cliente: {str(e)}"
