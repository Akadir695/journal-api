# syntax=docker/dockerfile:1

# ---------- builder ----------
  FROM python:3.12-slim AS builder

  COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
  
  ENV UV_COMPILE_BYTECODE=1 \
      UV_LINK_MODE=copy \
      UV_PYTHON_DOWNLOADS=never
  
  WORKDIR /app
  
  RUN --mount=type=cache,target=/root/.cache/uv \
      --mount=type=bind,source=uv.lock,target=uv.lock \
      --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
      uv sync --frozen --no-install-project --no-dev
  
  COPY . .
  
  RUN --mount=type=cache,target=/root/.cache/uv \
      uv sync --frozen --no-dev
  
  # ---------- runtime ----------
  FROM python:3.12-slim AS runtime
  
  ENV PYTHONDONTWRITEBYTECODE=1 \
      PYTHONUNBUFFERED=1 \
      PATH="/app/.venv/bin:$PATH"
  
  RUN useradd --create-home --uid 10001 appuser
  
  WORKDIR /app
  COPY --from=builder --chown=appuser:appuser /app /app
  
  USER appuser
  EXPOSE 8000
  
  HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
      CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').getcode()==200 else 1)"
  
  CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]