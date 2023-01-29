FROM tiangolo/uvicorn-gunicorn-fastapi:python3.10

# install pip packages at the beginning of the Dockerfile to make use of Docker layer caching
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# fastapi configuration via environment variables, see https://github.com/tiangolo/uvicorn-gunicorn-fastapi-docker
# default app module is app.app.main:app and app.main:app -> we need to specify explicitly
ENV APP_MODULE="plants.main:app"

COPY plants /app/plants
COPY ml_helpers /app/ml_helpers
COPY alembic /app/alembic
COPY config.toml /app/config.toml
COPY alembic.ini /app/alembic.ini
COPY prestart.sh /app/prestart.sh

# switch working directory to have module "plants" available
WORKDIR "/app/"