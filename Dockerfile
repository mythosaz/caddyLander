# Build stage for CodeMirror
FROM node:20-slim AS builder

WORKDIR /build

COPY package.json build.js ./
COPY src ./src

RUN npm install && npm run build

# Final stage
FROM python:3.12-slim

WORKDIR /app

# Install gzip utilities
RUN apt-get update && apt-get install -y gzip && rm -rf /var/lib/apt/lists/*

COPY server.py /app/server.py
COPY static /app/static
COPY content/content.json /app/content/content.json
COPY vendor/caddy/caddy.gz /app/vendor/caddy/caddy.gz

# Copy the built CodeMirror bundle from builder stage
COPY --from=builder /build/static/editor.bundle.js /app/static/editor.bundle.js

# Gunzip the caddy binary and make it executable
RUN gunzip /app/vendor/caddy/caddy.gz && \
    chmod +x /app/vendor/caddy/caddy

VOLUME ["/var/caddy"]

EXPOSE 8080

CMD ["python3", "/app/server.py"]
