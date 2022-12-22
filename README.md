# plants-backend
Flask-based RESTful Database Application for Tracking Plants

## Frontend
Open UI5-based web frontend, see [plants-frontend](https://github.com/stopwhispering/plants-frontend).

## Webserver / Reverse Proxy
The sample architecture uses NGINX and uWSGI as middleware. uWSGI can use the flask app returned by
the factory method in *app.py*. On local system one can use the Flask development server
instead (*python wsgi.py*).

![Architecture](static/architecture.png?raw=true "Architecture")

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

Create .env in same folder as docker-compose files file and insert connection string.
Example:
```
# postgres
CONNECTION_STRING="postgresql+psycopg2://plants:mypassword@postgres:5432/plants"
```

Create & Run Docker Container
```
# dev
docker-compose -f ./docker-compose.base.yml -f ./docker-compose.dev.yml up --build --detach

# prod
docker-compose -f ./docker-compose.base.yml -f ./docker-compose.prod.yml up --build --detach
```
Test API (dev): Open in Browser - http://plants.localhost/api/plants/
