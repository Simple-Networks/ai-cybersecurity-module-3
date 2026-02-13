FROM ghcr.io/astral-sh/uv:0.9.11-python3.12-alpine@sha256:bd3851aa1dcb48ad470b922db1a3411babfd264fcccb30f0dbf03d36d36ebd84

WORKDIR /app

ADD ./module-3 /app

WORKDIR /app

RUN uv sync --locked

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
