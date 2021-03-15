from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from plants.extensions.db import init_database_tables, engine
from plants.routers import (taxa, plants, images, events, property_names, properties, proposals,
                            functions, selection_data, api_biodiversity)
from plants.util.logger_utils import configure_root_logger


configure_root_logger()

COMMON_PREFIX = '/plants_tagger/backend'
app = FastAPI(docs_url=COMMON_PREFIX + "/docs", redoc_url=COMMON_PREFIX + "/redoc")

# allow cors on dev  # todo really only on dev
origins = [
    "http://localhost",
    "http://localhost:5000",
    "http://localhost:8000",
    "http://localhost:8080",
    ]
app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        )

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
