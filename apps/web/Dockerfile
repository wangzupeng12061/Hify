FROM node:24-bookworm-slim

ENV NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000

WORKDIR /app

RUN corepack enable && corepack prepare pnpm@11.8.0 --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/package.json
RUN pnpm install --frozen-lockfile --filter @hify/web...

COPY apps/web apps/web
RUN pnpm --filter @hify/web build

RUN useradd --create-home --shell /usr/sbin/nologin hify
USER hify

WORKDIR /app/apps/web
EXPOSE 3000

CMD ["node_modules/.bin/next", "start"]
