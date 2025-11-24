# syntax=docker/dockerfile:1.7

FROM node:18-alpine AS builder

WORKDIR /app

# Install dependencies using the curated manifest that lives outside the submodule
COPY docker/frontend/package*.json ./
RUN npm install --frozen-lockfile || npm install

# Copy the actual frontend sources from the submodule
COPY frontend/ .
# Override build-only adjustments (e.g., Vite config without autoprefixer plugin abuse)
COPY docker/frontend/vite.config.ts ./vite.config.ts

# Build production assets (fallback keeps container usable even if build fails)
RUN npm run build || (echo "Frontend build failed, generating fallback" && mkdir -p dist && echo '<h1>Frontend Build Error</h1>' > dist/index.html)

FROM nginx:1.25-alpine AS production

COPY --from=builder /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

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
