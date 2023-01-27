import pytest

from plants.modules.plant.models import Plant


def test_plant_valid(number):
    p = Plant()