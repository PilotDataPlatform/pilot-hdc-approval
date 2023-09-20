FROM python:3.9-buster AS base-image

ENV PYTHONDONTWRITEBYTECODE=true \
    PYTHONIOENCODING=UTF-8 \
    POETRY_VERSION=1.3.2 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false

ENV PATH="${POETRY_HOME}/bin:${PATH}"

WORKDIR /usr/src/app
RUN apt-get update && \
    apt-get install -y vim && \
    apt-get install -y less
RUN curl -sSL https://install.python-poetry.org | python3 -

COPY poetry.lock pyproject.toml ./

FROM base-image as web-image
RUN poetry install --no-dev --no-root --no-interaction
COPY . .
RUN chmod +x gunicorn_starter.sh

CMD ["python", "run.py"]

FROM base-image AS alembic-image
RUN apt-get update && \
    apt-get install -y postgresql-client
RUN poetry install --no-root --no-interaction
ENV ALEMBIC_CONFIG=alembic.ini

COPY . .
CMD psql ${DB_URI} -f migrations/scripts/create_approval_db.sql && \
psql ${DB_URI} -f migrations/scripts/create_approval_schema.sql && \
python3 -m alembic upgrade head
