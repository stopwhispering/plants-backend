import logging

from fastapi import FastAPI
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from plants import config
from plants.extensions.db import init_database_tables, engine
from plants.routers import (taxa, plants, images, events, property_names, properties, proposals,
                            functions, selection_data, api_biodiversity)
from plants.util.logger_utils import configure_root_logger

logger = logging.getLogger(__name__)

configure_root_logger(config.log_severity_console, config.log_severity_file)

COMMON_PREFIX = '/plants_tagger/backend'
app = FastAPI(
        docs_url=COMMON_PREFIX + "/docs",
        redoc_url=COMMON_PREFIX + "/redoc",
        openapi_url=COMMON_PREFIX + "/openapi.json"
        )

if config.allow_cors:
    origins = [
        "http://localhost",
        "http://localhost:5000",
        "http://localhost:8000",
        "http://localhost:8080",
        "http://localhost:8081",
        ]
    app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            )


# override 422 request validation error (pydantic models) to log them
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.error(exc)
    return await request_validation_exception_handler(request, exc)


app.include_router(taxa.router, prefix=COMMON_PREFIX)
app.include_router(plants.router, prefix=COMMON_PREFIX)
app.include_router(images.router, prefix=COMMON_PREFIX)
app.include_router(events.router, prefix=COMMON_PREFIX)
app.include_router(property_names.router, prefix=COMMON_PREFIX)
app.include_router(properties.router, prefix=COMMON_PREFIX)
app.include_router(proposals.router, prefix=COMMON_PREFIX)
app.include_router(functions.router, prefix=COMMON_PREFIX)
app.include_router(selection_data.router, prefix=COMMON_PREFIX)
app.include_router(api_biodiversity.router, prefix=COMMON_PREFIX)

init_database_tables(engine_=engine)
