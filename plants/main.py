from __future__ import annotations

import logging
from threading import Thread
from typing import Final

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from plants import local_config
from plants.extensions.config_values import Environment
from plants.extensions.db import create_db_engine
from plants.extensions.logging import configure_root_logger
from plants.extensions.orm import init_orm
from plants.modules.biodiversity.routes import router as biodiversity_router
from plants.modules.event.routes import router as event_router
from plants.modules.image.routes import router as image_router
from plants.modules.plant import routes as plant_router
from plants.modules.pollination.prediction.predict_germination import (
    get_germination_days_model,
    get_germination_probability_model,
)
from plants.modules.pollination.prediction.predict_pollination import (
    get_probability_of_seed_production_model,
)
from plants.modules.pollination.prediction.predict_ripening import get_ripening_days_model
from plants.modules.pollination.routes import router as pollination_router
from plants.modules.taxon.routes import router as taxon_router
from plants.shared.routes import router as shared_router

configure_root_logger(
    log_severity_console=local_config.log_settings.log_level_console,
    log_severity_file=local_config.log_settings.log_level_file,
    log_file_path=local_config.log_settings.log_file_path,
)
logger = logging.getLogger(__name__)

COMMON_PREFIX: Final[str] = "/api"
app = FastAPI(
    title="Plants",
    docs_url=COMMON_PREFIX + "/docs" if local_config.environment == Environment.DEV else None,
    redoc_url=COMMON_PREFIX + "/redoc" if local_config.environment == Environment.DEV else None,
    openapi_url=COMMON_PREFIX + "/openapi.json"
    if local_config.environment == Environment.DEV
    else None,
)

# we are using this backend for two frontends: plants (same hostname, no cors
# required) and pollinations (cors required)
ORIGINS: Final[list[str]] = [
    "http://pollination.localhost",
    "https://pollination." + local_config.hostname,
]
# additional CORS for development only
if local_config.allow_cors:
    # if config.allow_cors:
    ORIGINS.extend(
        [
            "http://localhost:5000",
            "http://localhost:8080",
            "http://localhost:8085",
        ]
    )
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(taxon_router, prefix=COMMON_PREFIX)
app.include_router(plant_router.router, prefix=COMMON_PREFIX)
app.include_router(image_router, prefix=COMMON_PREFIX)
app.include_router(event_router, prefix=COMMON_PREFIX)
app.include_router(pollination_router, prefix=COMMON_PREFIX)
app.include_router(shared_router, prefix=COMMON_PREFIX)
app.include_router(biodiversity_router, prefix=COMMON_PREFIX)


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Starting up, starting with DB connection")
    engine = create_db_engine(local_config.connection_string)
    await init_orm(engine=engine)

    # load pickled models in bg tasks
    Thread(target=get_probability_of_seed_production_model).start()
    Thread(target=get_ripening_days_model).start()
    Thread(target=get_germination_probability_model).start()
    Thread(target=get_germination_days_model).start()
