FROM python:3.12-slim AS base
RUN pip install --no-cache-dir uv
WORKDIR /app/apps/api
COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev
COPY apps/api .
RUN uv sync --frozen --no-dev

FROM base AS dev
RUN uv sync --frozen
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "api.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS prod
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "api.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
