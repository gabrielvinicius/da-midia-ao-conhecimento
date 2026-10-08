# Stage 1: build da aplicação React
FROM node:22-alpine AS builder

WORKDIR /app

# Instala exatamente as versões do package-lock.json (cache de camadas)
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .

# Se o build falhar, a imagem não é gerada (antes, publicava uma página de erro em silêncio)
RUN npm run build

# Stage 2: servir os arquivos estáticos com Nginx
FROM nginx:1.31-alpine AS production

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Usuário sem privilégios de root
RUN addgroup -S appgroup && adduser -S appuser -G appgroup \
    && chown -R appuser:appgroup /usr/share/nginx/html \
    && chown -R appuser:appgroup /var/cache/nginx \
    && chown -R appuser:appgroup /var/log/nginx \
    && chown -R appuser:appgroup /etc/nginx/conf.d \
    && touch /var/run/nginx.pid \
    && chown -R appuser:appgroup /var/run/nginx.pid

USER appuser

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
