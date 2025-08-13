Recomendações prioritárias (curto prazo)
Alinhar versões e build
Em pyproject.toml: requires-python = ">=3.12"; adicionar httpx, pydantic-settings; mover black/isort para extras.
Em Dockerfile: corrigir instalação com uv.
Apply to pyproject.to...
Apresentação
Extrair rotas/DTOs para app/presentation e deixar main.py apenas criar FastAPI e incluir routers.
Infraestrutura
Mover chamadas HTTP para app/infrastructure/services/* com httpx.AsyncClient.
Tools na camada de aplicação passam a depender de interfaces (injeção de dependência).
Aplicação / LangGraph
Introduzir StateGraph com ProxyAgentState (ou SchedulingAgentState), nó de roteamento explícito, e registro de nós via decorator @register_node.
Substituir heurísticas no main.py por roteamento do supervisor no grafo.
Assincronia
Tornar tools async e remover requests. Exemplo:
Apply to pyproject.to...
Configurações e logging
Criar app/infrastructure/config/settings.py com Pydantic Settings.
Adotar structured logging (ex.: structlog ou logging com JSON).
Segurança
Remover eval do math_tool.py ou substituir por parser matemático seguro.
Estrutura alvo (mínima) alinhada à Onion Architecture
app/domain/ (entidades/VOs/serviços/eventos; p.ex. AgentHeuristic, EpisodicMemory)
app/application/
agent/ (state/, nodes/, edges/, registry.py, proxy_agent_builder.py)
tool/ (tools assíncronos que chamam serviços via interfaces)
use_cases/ (se necessário)
app/infrastructure/
services/ (company_client.py, budget_client.py)
database/ (SQLAlchemy async + checkpointer)
config/ (settings.py)
app/presentation/
routers/ (FastAPI)
dto/ (Pydantic models)
alembic/ (migrations)