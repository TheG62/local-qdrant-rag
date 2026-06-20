# Server-Image (API + Yjs-Sync)
FROM node:22-alpine AS build
WORKDIR /app
RUN corepack enable
COPY package.json ./
COPY apps/server/package.json apps/server/package.json
RUN pnpm install --filter @vct/server... --frozen-lockfile=false
COPY apps/server apps/server
RUN pnpm --filter @vct/server build

FROM node:22-alpine
WORKDIR /app
RUN corepack enable
ENV NODE_ENV=production
COPY package.json ./
COPY apps/server/package.json apps/server/package.json
RUN pnpm install --filter @vct/server --prod --frozen-lockfile=false
COPY --from=build /app/apps/server/dist apps/server/dist
ENV DATA_DIR=/data
VOLUME /data
EXPOSE 4000
CMD ["node", "apps/server/dist/index.js"]
