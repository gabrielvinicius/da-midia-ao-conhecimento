# syntax=docker/dockerfile:1
# Site da documentação (docs/ e zensical.toml), publicado pelo serviço "docs"
# do Compose. Contexto: a raiz do repositório, com a lista própria em
# docker/docs.Dockerfile.dockerignore (a .dockerignore da raiz exclui docs/).

# Stage 1: gera o site. Em modo estrito, um link para página inexistente
# reprova o build, e a versão anterior continua no ar.
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /src

COPY requirements-docs.txt ./
RUN pip install --no-cache-dir -r requirements-docs.txt

COPY zensical.toml ./
COPY docs ./docs
RUN zensical build --strict --clean

# Stage 2: arquivos estáticos no Nginx, como a interface.
FROM nginx:1.31-alpine AS production

COPY --from=builder /src/site /usr/share/nginx/html
COPY docker/docs-nginx.conf /etc/nginx/conf.d/default.conf

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
