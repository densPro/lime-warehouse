FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
COPY pyproject.toml ./
COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic
RUN pip install .
EXPOSE 8004
# Apply migrations, seed, then start. Set SEED_DEMO=<fruits|vegetables|computers> (see `python -m lime_warehouse.seed --list`)
# to load a sample set on every start, or run it on demand: python -m lime_warehouse.seed --demo <name>
CMD ["sh", "-c", "alembic upgrade head && python -m lime_warehouse.seed ${SEED_DEMO:+--demo \"$SEED_DEMO\"} && uvicorn lime_warehouse.main:app_factory --factory --host 0.0.0.0 --port 8004"]
