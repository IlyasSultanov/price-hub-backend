FROM python:3.12-slim

WORKDIR /app

ENV UV_PROJECT_ENVIRONMENT=/usr/local

COPY pyproject.toml uv.lock ./

RUN pip install --upgrade pip \
    && pip install uv \
    && uv sync --locked --no-dev

COPY . .

EXPOSE 8111

CMD ["uv", "run", "gunicorn", "app.main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8111"]

