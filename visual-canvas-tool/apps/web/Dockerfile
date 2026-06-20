# Web-Client (statisches Build, via nginx ausgeliefert)
FROM node:22-alpine AS build
WORKDIR /app
RUN corepack enable
COPY package.json ./
COPY apps/web/package.json apps/web/package.json
RUN pnpm install --filter @vct/web... --frozen-lockfile=false
COPY apps/web apps/web
ARG VITE_API_URL=http://localhost:4000
ARG VITE_WS_URL=ws://localhost:4000
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WS_URL=$VITE_WS_URL
RUN pnpm --filter @vct/web build

FROM nginx:alpine
COPY --from=build /app/apps/web/dist /usr/share/nginx/html
EXPOSE 80
