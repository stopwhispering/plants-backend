"""Run the app on local dev system."""
from __future__ import annotations

import asyncio
import faulthandler
import sys

import uvicorn

if __name__ == "__main__":
    # required to make psycopg3 async work on windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    faulthandler.enable()

    uvicorn.run(
        "plants.main:app",
        host="localhost",
        port=5000,
        # reload=True
    )

