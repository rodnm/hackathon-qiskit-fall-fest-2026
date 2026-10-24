# Imagen del backend: FastAPI + paquete compartido qap + datos (boceto de S8 del plan)
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Primero solo manifiestos: las capas de dependencias se cachean entre builds
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY backend ./backend
COPY data ./data
COPY results ./results

RUN uv sync --frozen --no-dev && useradd -m app
USER app

HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
    CMD python -c "import urllib.request as u; u.urlopen('http://localhost:8000/api/health')"

CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
