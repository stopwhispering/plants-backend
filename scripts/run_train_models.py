from __future__ import annotations

import asyncio
import sys

from plants.modules.pollination.prediction.train_germination import train_model_for_germination_days

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from plants.modules.pollination.prediction.train_florescence import (  # noqa
    train_model_for_florescence_probability,
)


if __name__ == "__main__":
    # results, shap_values, df_preprocessed = asyncio.run(train_model_for_probability_of_seed_production())
    # for key, value in results.items():
    #     print(f"{key}: {value}")

    # results = asyncio.run(train_model_for_ripening_days())
    # for key, value in results.items():
    #     print(f"{key}: {value}")

    # results = asyncio.run(train_model_for_germination_probability())
    # for key, value in results.items():
    #     print(f"{key}: {value}")

    # results = asyncio.run(train_model_for_florescence_probability())
    # for key, value in results.items():
    #     print(f"{key}: {value}")

    results = asyncio.run(train_model_for_germination_days())
    for key, value in results.items():
        print(f"{key}: {value}")
