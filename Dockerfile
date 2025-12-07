FROM python:3.12-slim

WORKDIR /app

COPY server.py /app/server.py
COPY static /app/static
COPY content/content.json /app/content/content.json

VOLUME ["/var/caddy"]

EXPOSE 8080

CMD ["python3", "/app/server.py"]
