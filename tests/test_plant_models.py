import pytest
from sqlalchemy.exc import IntegrityError

from plants.modules.plant.models import Plant


def test_plant_invalid(db):
    plant = Plant(field_number='A100')

    db.add(plant)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    p = db.query(Plant).filter(Plant.field_number == 'A100').first()
    assert p is None


def test_plant_valid(db):
    plant = Plant(plant_name='Aloe Vera',)
    db.add(plant)
    db.commit()

    p = Plant.by_name(plant.plant_name, db=db)
    assert p.plant_name == plant.plant_name
    assert p.id is not None


def test_plant_duplicate_name(db, plant_valid):
    db.add(Plant(plant_name='Aloe Vera',))
    db.commit()

    db.add(Plant(plant_name='Aloe Vera',))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

