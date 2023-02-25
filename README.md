# plants-backend
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
<br>
FastAPI-based RESTful Database Application for Tracking Plants

## Frontend
OpenUI5/TypeScript-based web frontend, see [plants-frontend-ts](https://github.com/stopwhispering/plants-frontend-ts).

## Webserver / Reverse Proxy
The sample architecture makes use of the following components:

Docker and Docker Compose are used to run the application in a container.
- [Docker](https://www.docker.com/) for containerization
- [Docker Compose](https://docs.docker.com/compose/) for defining and running multi-container Docker applications

Gunicorn and Uvicorn are contained in the [official FastAPI Docker image](https://hub.docker.com/r/tiangolo/uvicorn-gunicorn-fastapi). With
almost all routes being asynchronous, switching to a Gunicorn alternative would probably be a good idea for the future.
- [Gunicorn](https://gunicorn.org/) as a process manager
- [Guvicorn](https://www.uvicorn.org/) as an ASGI web server

Traefik takes care of routing the traffic to the correct container and provides SSL encryption via Let's Encrypt.
- [Traefik](https://traefik.io/) as reverse proxy and load balancer
- [Let's Encrypt](https://letsencrypt.org/) for free SSL certificates

Traefik is expected to be running as described in [traefik-via-docker-with-sample-services](https://github.com/stopwhispering/traefik-via-docker-with-sample-services).

FastAPI is used as the web framework. It is based on Starlette and Pydantic, and is fully ASGI-compliant.
- [FastAPI](https://fastapi.tiangolo.com/) as web framework
- [Starlette](https://www.starlette.io/) as ASGI framework/toolkit
- [Pydantic](https://pydantic-docs.helpmanual.io/) for data validation and settings management

PostgreSQL is used as the database, and SQLAlchemy is used as the ORM.
- [PostgreSQL](https://www.postgresql.org/) as database
- [SQLAlchemy](https://www.sqlalchemy.org/) as ORM

My sample PostgreSQL database is running in a separate container as described in [postgresql-via-traefik](https://github.com/stopwhispering/postgresql-via-traefik).

One can, of course, run the application standalone on a local system, provided a running database exists,  with Uvicorn only:
```
uvicorn plants.main:app --host localhost --port 5000
```

![Architecture](static/plants_backend_deployment_architecture.png?raw=true "Architecture")

## Configuration
plants-backend requires environment-specific settings to be set via environment variables, preferably
via a `.env` file, see `.example.env` for an example.
The following settings are required:
- ENVIRONMENT (dev or prod)
- HOSTNAME (e.g. localhost or example.com)
- CONNECTION_STRING (e.g. postgresql+asyncpg://plants:mypassword@postgres.localhost:5432/plants)
- LOG_SETTINGS__LOG_LEVEL_CONSOLE (DEBUG, INFO, WARNING, or ERROR)
- LOG_SETTINGS__LOG_LEVEL_FILE (DEBUG, INFO, WARNING, or ERROR)
- LOG_SETTINGS__LOG_FILE_PATH (e.g. /common/plants/plants.log)

Optional settings:
- MAX_IMAGES_PER_TAXON (default: 20)
- ALLOW_CORS (default: false)
- LOG_SETTINGS__IGNORE_MISSING_IMAGE_FILES (default: False)

## Database
The sample architecture uses PostgreSQL as a database. Thanks to SQLAlchemy, switching to any other major
RDBMS should work by simply changing the connection string.

Some specific logic is implemented, though, for auto-incrementing IDs as well as for enumerations that might cause problems
with other databases.

### Database Migration
Database migration is handled by [Alembic](https://alembic.sqlalchemy.org/en/latest/). The migration scripts are located in the ./alembic/versions folder. The
official FastAPI Docker image contains a hook that automatically runs the migration scripts on startup (see `./prestart.sh`).

## Execution Mode
The majority of path functions are asynchronous, and the application is therefore designed to run in an asynchronous mode. It requires an
asynchronous db driver like [asyncpg](https://magicstack.github.io/asyncpg/current/) which is mentioned in the project requirements file.
Access to file system is running in a synchronous mode, too. External API calls are run in an external thread pool executor to avoid blocking the event loop.
Long-running tasks are run as background tasks for the same reason.

## Deployment
Git Clone
```
git clone https://github.com/stopwhispering/plants-backend.git
cd plants-backend
```
Create folder for images, db, and models
```
# linux
mkdir -p /common/plants/db

# windows
mkdir /common/plants/db
```

Create `.env` in same folder as docker-compose files file and insert environment-specific settings, see configuration
options above and `.example.env` for help.

Create & Run Docker Container
Deployment with the contained docker-compose and Dockerfile files requires a running
[Traefik reverse proxy](https://github.com/stopwhispering/traefik-via-docker-with-sample-services) as well as
a running [PostgreSQL database](https://github.com/stopwhispering/postgresql-via-traefik).
```
# dev
docker-compose -f ./docker-compose.base.yml -f ./docker-compose.dev.yml up --build --detach

# prod
docker-compose -f ./docker-compose.base.yml -f ./docker-compose.prod.yml up --build --detach
```

Test API (dev): Open in Browser - http://plants.localhost/api/plants/

Test API (prod): Open in Browser - http://plants.example-com/api/plants/
