FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/backend/src \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/backend/.venv/bin:${PATH}"

WORKDIR /app/backend

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend/ ./
RUN uv sync --frozen --no-dev

RUN useradd --create-home --shell /usr/sbin/nologin hify
USER hify

EXPOSE 8000

CMD ["uvicorn", "hify.bootstrap.api:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
