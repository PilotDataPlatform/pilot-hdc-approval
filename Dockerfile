FROM docker-registry.ebrains.eu/hdc-services-image/base-image:python-3.10.12-v2 AS base-image

ENV PYTHONDONTWRITEBYTECODE=true \
    PYTHONIOENCODING=UTF-8 \
    POETRY_VERSION=1.3.2 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false

ENV PATH="${POETRY_HOME}/bin:${PATH}"

RUN apt-get update && \
    apt-get install -y vim && \
    apt-get install -y less
RUN curl -sSL https://install.python-poetry.org | python3 -

COPY poetry.lock pyproject.toml ./

FROM base-image as approval-image
RUN poetry install --no-dev --no-root --no-interaction
COPY . .
RUN chmod +x gunicorn_starter.sh

RUN chown -R app:app /app
USER app

CMD ["python", "run.py"]

FROM base-image AS alembic-image
RUN apt-get update && \
    apt-get install -y postgresql-client
RUN poetry install --no-root --no-interaction
ENV ALEMBIC_CONFIG=alembic.ini

COPY . .

RUN chown -R app:app /app
USER app

CMD psql ${DB_URI} -f migrations/scripts/create_approval_db.sql && \
psql ${DB_URI} -f migrations/scripts/create_approval_schema.sql && \
python3 -m alembic upgrade head
