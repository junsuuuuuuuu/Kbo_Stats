FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    ML_N_JOBS=1

WORKDIR /workspace

COPY backend/pyproject.toml backend/README.md ./backend/
COPY backend/app ./backend/app
COPY backend/alembic ./backend/alembic
COPY backend/alembic.ini ./backend/alembic.ini
COPY backend/scripts ./backend/scripts
COPY data/processed ./data/processed

RUN python -m pip install --upgrade pip && \
    python -m pip install "./backend[ml]"

WORKDIR /workspace/backend

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
