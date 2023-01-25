# plants-backend
Flask-based RESTful Database Application for Tracking Plants

## Frontend
Open UI5-based web frontend, see [plants-frontend](https://github.com/stopwhispering/plants-frontend).

## Webserver / Reverse Proxy
The sample architecture uses NGINX and uWSGI as middleware. uWSGI can use the flask app returned by
the factory method in *app.py*. On local system one can use the Flask development server
instead (*python wsgi.py*).

*(todo update text)*

![Architecture](static/plants_backend_deployment_architecture.png?raw=true "Architecture")

## Configuration
see *config.py* and *config_local.py*, the latter used to set environment-specific
settings like db connection string, logging minimum severity, or to allow CORS
on development environment

## Database
I’m using SQLite. Thanks to SQLAlchemy (ORM), switching to any other major
relational database should work by simply changing connection string via environment
variable..
Some specific logic is implemented, though, to manage the point in time when auto-incremented
IDs are determined.

## Dependencies
- Flask
- Flask RESTful
- SQLAlchemy
- Pillow
- Werkzeug
- piexif
- pykew
- requests



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
Adjust hostnames in docker-compose.prod.yml (prod only)

Create .env in same folder as docker-compose files file and insert environment-specific settings.
Example DEV:
```
ENVIRONMENT=dev
#CONNECTION_STRING=postgresql+psycopg2://plants:mypassword@postgres:5432/plants
# max occurrence images downloaded from inaturalist etc. per taxon (default: 20)
MAX_IMAGES_PER_TAXON=5
# allow CORS in FastAPI app (default: false)
ALLOW_CORS=True
LOG_SETTINGS__LOG_LEVEL_CONSOLE=DEBUG
LOG_SETTINGS__LOG_LEVEL_FILE=INFO
LOG_SETTINGS__LOG_FILE_PATH=/common/plants/plants.log
# don't throw exception if image file is missing (default: False)
LOG_SETTINGS__IGNORE_MISSING_IMAGE_FILES=True
```

Example PROD:
```
ENVIRONMENT=prod
CONNECTION_STRING="postgresql+psycopg2://plants:mypassword@postgres:5432/plants"

LOGSETTINGS__LOG_LEVEL_CONSOLE=INFO
LOGSETTINGS__LOG_LEVEL_FILE=INFO
LOGSETTINGS__LOG_FILE_PATH=/common/plants/plants.log
```

Create & Run Docker Container
```
# dev
docker-compose -f ./docker-compose.base.yml -f ./docker-compose.dev.yml up --build --detach

# prod
docker-compose -f ./docker-compose.base.yml -f ./docker-compose.prod.yml up --build --detach
```
Test API (dev): Open in Browser - http://plants.localhost/api/plants/
