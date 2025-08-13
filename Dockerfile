FROM python:3.12-slim

# Instalar uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copiar arquivos de configuração primeiro
COPY pyproject.toml uv.lock* ./

# Instalar dependências
RUN uv sync --no-install-project --frozen || uv sync --no-install-project

# Copiar o resto do código
COPY . .

EXPOSE 8080

# Usar uv run para executar uvicorn
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
