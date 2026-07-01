FROM node:22-slim AS base
RUN corepack enable
WORKDIR /app
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY apps/web/package.json apps/web/package.json
RUN pnpm install --frozen-lockfile
COPY apps/web apps/web

FROM base AS dev
WORKDIR /app/apps/web
EXPOSE 3000
CMD ["pnpm", "dev"]

FROM base AS builder
WORKDIR /app/apps/web
RUN pnpm build

FROM builder AS prod
WORKDIR /app/apps/web
EXPOSE 3000
CMD ["pnpm", "start"]
