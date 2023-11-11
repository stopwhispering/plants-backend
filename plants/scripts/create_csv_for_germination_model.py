from __future__ import annotations

import asyncio
import logging

from plants.modules.pollination.prediction.seed_planting_data import assemble_seed_planting_data
from plants.modules.pollination.prediction.train_germination import \
    train_model_for_germination_probability, create_germination_features, \
    train_model_for_germination_days

logging.basicConfig(level=logging.DEBUG, force=True)
logger = logging.getLogger(__name__)


async def create_csv():
    feature_container = create_germination_features()
    df_all = await assemble_seed_planting_data(feature_container=feature_container)
    df_all.to_csv('seed_plantings.csv', index=False)


async def start():
    # await create_csv()
    # await train_model_for_germination_probability()
    await train_model_for_germination_days()



asyncio.run(start())
