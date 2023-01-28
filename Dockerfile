FROM tiangolo/uvicorn-gunicorn-fastapi:python3.10

# install pip packages at the beginning of the Dockerfile to make use of Docker layer caching
COPY ./requirements.txt /src/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /src/requirements.txt

# fastapi configuration via environment variables, see https://github.com/tiangolo/uvicorn-gunicorn-fastapi-docker
# default app module is app.app.main:app and app.main:app -> we need to specify explicitly
ENV APP_MODULE="plants.main:app"

COPY plants /src/plants
COPY ml_helpers /src/ml_helpers
COPY alembic /src/alembic
COPY config.toml /src/config.toml

# switch working directory to have module "plants" available
WORKDIR "/src/"

CMD ["alembic", "upgrade", "head"]