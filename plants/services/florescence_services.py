from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from plants.models.plant_models import Plant
from plants.models.pollination_models import Florescence, FlorescenceStatus, Context, Pollination, COLORS_MAP_TO_RGB
from plants.util.ui_utils import parse_api_date, format_api_date
from plants.validation.pollination_validation import PActiveFlorescence, PRequestEditedFlorescence, \
    PPlantForNewFlorescence, PRequestNewFlorescence


def _read_available_colors_rgb(plant: Plant, db: Session):
    used_colors_t = db.query(Pollination.label_color).filter(Pollination.seed_capsule_plant_id == plant.id,
                                                             Pollination.ongoing).all()
    # un-tuple
    used_colors = [t[0] for t in used_colors_t]
    available_color_names = [c for c in COLORS_MAP_TO_RGB.keys() if c not in used_colors]
    available_colors_rgb = [COLORS_MAP_TO_RGB[c] for c in available_color_names]
    return available_colors_rgb


def read_plants_for_new_florescence(db: Session) -> list[PPlantForNewFlorescence]:
    query = db.query(Plant).filter((Plant.hide.is_(False)) | (Plant.hide.is_(None)))
    plants: list[Plant] = query.all()

    plants_for_new_florescence = []
    for p in plants:
        plants_for_new_florescence.append(PPlantForNewFlorescence(
                                            plant_id=p.id,
                                            plant_name=p.plant_name,
                                            genus=p.taxon.genus if p.taxon else None))
    return plants_for_new_florescence


def read_active_florescences(db: Session) -> list[PActiveFlorescence]:
    query = (db.query(Florescence)
             .filter(Florescence.florescence_status.in_({FlorescenceStatus.FLOWERING.value,
                                                         FlorescenceStatus.INFLORESCENCE_APPEARED.value}))
             )
    florescences_orm = query.all()

    florescences = []
    for f in florescences_orm:
        f: Florescence
        f_dict = {
            'id': f.id,
            'plant_id': f.plant_id,
            'plant_name': f.plant.plant_name if f.plant else None,
            'florescence_status': f.florescence_status,
            'inflorescence_appearance_date': format_api_date(f.inflorescence_appearance_date),
            'comment': f.comment,
            'branches_count': f.branches_count,
            'flowers_count': f.flowers_count,
            'first_flower_opening_date': format_api_date(f.first_flower_opening_date),
            'last_flower_closing_date': format_api_date(f.last_flower_closing_date),

            'available_colors_rgb': _read_available_colors_rgb(plant=f.plant, db=db),
        }
        florescences.append(PActiveFlorescence.parse_obj(f_dict))

    return florescences


def update_active_florescence(edited_florescence_data: PRequestEditedFlorescence, db: Session):
    florescence: Florescence = db.query(Florescence).filter(
        Florescence.id == edited_florescence_data.id).first()

    # technical validation
    assert florescence is not None
    assert florescence.plant_id == edited_florescence_data.plant_id

    # semantic validation
    assert FlorescenceStatus.has_value(edited_florescence_data.florescence_status)

    florescence.florescence_status = edited_florescence_data.florescence_status
    florescence.inflorescence_appearance_date = parse_api_date(edited_florescence_data.inflorescence_appearance_date)
    florescence.comment = edited_florescence_data.comment
    florescence.first_flower_opening_date = parse_api_date(edited_florescence_data.first_flower_opening_date)
    florescence.last_flower_closing_date = parse_api_date(edited_florescence_data.last_flower_closing_date)
    florescence.branches_count = edited_florescence_data.branches_count
    florescence.flowers_count = edited_florescence_data.flowers_count

    florescence.last_update_at = datetime.now()
    florescence.last_update_context = Context.API.value

    db.commit()


def create_new_florescence(new_florescence_data: PRequestNewFlorescence, db: Session):

    assert FlorescenceStatus.has_value(new_florescence_data.florescence_status)
    plant = Plant.get_plant_by_plant_id(plant_id=new_florescence_data.plant_id, db=db, raise_exception=True)

    florescence = Florescence(
        plant_id=new_florescence_data.plant_id,
        plant=plant,
        florescence_status=new_florescence_data.florescence_status,
        inflorescence_appearance_date=parse_api_date(new_florescence_data.inflorescence_appearance_date),
        comment=new_florescence_data.comment,

        creation_at=datetime.now(),
        creation_context=Context.API.value  # noqa
    )

    db.add(florescence)
    db.commit()


def remove_florescence(florescence_id: int, db: Session):
    """ Delete a florescence """
    florescence: Florescence = db.query(Florescence).filter(Florescence.id == florescence_id).first()
    if not florescence:
        raise HTTPException(500, detail={'message': 'Florescence attempt not found'})
    if florescence.pollinations:
        raise HTTPException(500, detail={'message': 'Florescence has pollinations'})
    db.delete(florescence)
    db.commit()
