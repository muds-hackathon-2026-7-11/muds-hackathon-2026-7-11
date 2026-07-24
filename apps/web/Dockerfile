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
# NEXT_PUBLIC_接頭辞の変数はnext build時にブラウザ向けJSへ焼き込まれるため、
# docker-compose側のenv_file(コンテナ起動時にしか効かない)ではなくbuild argsで渡す。
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN pnpm build

FROM builder AS prod
WORKDIR /app/apps/web
EXPOSE 3000
CMD ["pnpm", "start"]
