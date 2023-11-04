FROM python:3.11 as requirements-stage
WORKDIR /tmp
RUN pip3 install poetry
COPY ./pyproject.toml ./poetry.lock* /tmp/
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

FROM tiangolo/uvicorn-gunicorn-fastapi:python3.11
# switch working directory to have module "plants" available
WORKDIR "/app/"
COPY --from=requirements-stage /tmp/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# fastapi configuration via environment variables, see https://github.com/tiangolo/uvicorn-gunicorn-fastapi-docker
# default app module is app.app.main:app and app.main:app -> we need to specify explicitly
ENV APP_MODULE="plants.main:app"

COPY ./prestart.sh ./alembic.ini /app/
COPY alembic /app/alembic
COPY config.toml /app/config.toml
COPY plants/modules/pollination/prediction/ml_helpers /app/ml_helpers
COPY plants /app/plants
COPY scripts /app/scripts
