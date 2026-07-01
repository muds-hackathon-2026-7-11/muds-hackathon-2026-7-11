FROM python:3.12-slim AS base
RUN pip install --no-cache-dir uv
WORKDIR /app/services/slack-bot
COPY services/slack-bot/pyproject.toml services/slack-bot/uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev
COPY services/slack-bot .
RUN uv sync --frozen --no-dev

FROM base AS dev
RUN uv sync --frozen
CMD ["uv", "run", "slack-bot"]

FROM base AS prod
CMD ["uv", "run", "slack-bot"]
