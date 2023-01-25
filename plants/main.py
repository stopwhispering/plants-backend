import logging
from typing import Final

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from plants import local_config
from plants.extensions.db import init_database_tables, engine
from plants.routes import (taxonomy, plants, images, events, property_names, properties, proposals,
                           selection_data, biodiversity_apis, pollinations, florescences)
from plants.util.logger_utils import configure_root_logger

configure_root_logger(log_severity_console=local_config.log_settings.log_level_console,
                      log_severity_file=local_config.log_settings.log_level_file,
                      log_file_path=local_config.log_settings.log_file_path)
logger = logging.getLogger(__name__)

COMMON_PREFIX: Final[str] = '/api'
app = FastAPI(
    docs_url=COMMON_PREFIX + "/docs",
    redoc_url=COMMON_PREFIX + "/redoc",
    openapi_url=COMMON_PREFIX + "/openapi.json"
)

# we are using this backend for two frontends: plants (same hostname, no cors required) and pollinations (cors required)
ORIGINS: Final[list[str]] = ["http://pollination.localhost",
                             "https://pollination.astroloba.net", ]
# additional CORS for development only
if local_config.allow_cors:
    # if config.allow_cors:
    ORIGINS.extend([
        "http://localhost:5000",
        "http://localhost:8080",
    ])
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# # override 422 request validation error (pydantic models) to log them
# # todo deprecated
# @app.exception_handler(RequestValidationError)
# async def validation_exception_handler(request, exc):
#     logger.error(exc)
#     return await request_validation_exception_handler(request, exc)


app.include_router(taxonomy.router, prefix=COMMON_PREFIX)
app.include_router(plants.router, prefix=COMMON_PREFIX)
app.include_router(images.router, prefix=COMMON_PREFIX)
app.include_router(events.router, prefix=COMMON_PREFIX)
app.include_router(property_names.router, prefix=COMMON_PREFIX)
app.include_router(properties.router, prefix=COMMON_PREFIX)
app.include_router(proposals.router, prefix=COMMON_PREFIX)
app.include_router(selection_data.router, prefix=COMMON_PREFIX)
app.include_router(biodiversity_apis.router, prefix=COMMON_PREFIX)
app.include_router(pollinations.router, prefix=COMMON_PREFIX)
app.include_router(florescences.router, prefix=COMMON_PREFIX)

init_database_tables(engine_=engine)
