from __future__ import annotations

import asyncio
import logging

from plants.modules.pollination.prediction.pollination_data import assemble_pollination_data
from plants.modules.pollination.prediction.train_ripening import (
    _create_features,
    train_model_for_ripening_days,
)

logging.basicConfig(level=logging.DEBUG, force=True)
logger = logging.getLogger(__name__)


async def create_csv():
    feature_container = _create_features()
    df_all = await assemble_pollination_data(feature_container=feature_container)
    df_all.to_csv('df_all.csv', index=False)


async def train():
    await train_model_for_ripening_days()


async def start():
    await create_csv()
    # await train()


asyncio.run(start())
