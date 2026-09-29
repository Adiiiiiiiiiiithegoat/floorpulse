FROM node:24-alpine AS build
WORKDIR /web
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npx vite build

FROM caddy:2-alpine
COPY --from=build /web/dist /srv
COPY Caddyfile /etc/caddy/Caddyfile
