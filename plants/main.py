import logging
from typing import Final

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from plants import local_config
from plants.extensions.config_values import Environment
from plants.extensions.db import create_db_engine
from plants.extensions.orm import init_orm
from plants.modules.event.routes import router as event_router
from plants.modules.image.routes import router as image_router
from plants.modules.plant import routes as plant_router
from plants.modules.pollination.routes import router as pollination_router
from plants.modules.taxon.routes import router as taxon_router
from plants.shared.routes import router as shared_router
from plants.modules.biodiversity.routes import router as biodiversity_router
from plants.extensions.logging import configure_root_logger

configure_root_logger(log_severity_console=local_config.log_settings.log_level_console,
                      log_severity_file=local_config.log_settings.log_level_file,
                      log_file_path=local_config.log_settings.log_file_path)
logger = logging.getLogger(__name__)

COMMON_PREFIX: Final[str] = '/api'
app = FastAPI(
    title="Plants",
    docs_url=COMMON_PREFIX + "/docs" if local_config.environment == Environment.DEV else None,
    redoc_url=COMMON_PREFIX + "/redoc" if local_config.environment == Environment.DEV else None,
    openapi_url=COMMON_PREFIX + "/openapi.json" if local_config.environment == Environment.DEV else None,
)

# we are using this backend for two frontends: plants (same hostname, no cors required) and pollinations (cors required)
ORIGINS: Final[list[str]] = ["http://pollination.localhost",
                             "https://pollination." + local_config.hostname, ]
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


app.include_router(taxon_router, prefix=COMMON_PREFIX)
app.include_router(plant_router.router, prefix=COMMON_PREFIX)
app.include_router(image_router, prefix=COMMON_PREFIX)
app.include_router(event_router, prefix=COMMON_PREFIX)
app.include_router(pollination_router, prefix=COMMON_PREFIX)
app.include_router(shared_router, prefix=COMMON_PREFIX)
app.include_router(biodiversity_router, prefix=COMMON_PREFIX)


@app.on_event("startup")
async def startup_event():
    logger.info("Starting up, starting with DB connection")
    engine = create_db_engine(local_config.connection_string)
    await init_orm(engine=engine)
