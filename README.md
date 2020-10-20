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
I’m using SQLite. Due to SQLAlchemy (declarative system), switching to any other major
relational database should work by simply changing connection string in config_local.py.
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

## Still to be Done...
- [ ] some instructions on installation
- [ ] install with PyPi
- [ ] dockerize
- [ ] still some todo's in sources