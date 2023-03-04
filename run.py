"""Run the app on local dev system."""
from __future__ import annotations

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "plants.main:app",
        host="localhost",
        port=5000,
        # reload=True
    )
