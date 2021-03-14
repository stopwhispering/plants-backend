from fastapi import APIRouter, Depends
import logging
from sqlalchemy.orm import Session

from plants.util.ui_utils import get_message
from plants.validation.property_validation import PResultsPropertyNames
from plants.models.property_models import PropertyCategory
from plants.dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
        prefix="/property_names",
        tags=["property_names"],
        responses={404: {"description": "Not found"}},
        )


@router.get("/", response_model=PResultsPropertyNames)
async def get_property_names(db: Session = Depends(get_db)):
    category_obj = db.query(PropertyCategory).all()
    categories = {}
    for cat in category_obj:
        categories[cat.category_name] = [{'property_name':    p.property_name,
                                          'property_name_id': p.id,
                                          'countPlants':      len(p.property_values)
                                          } for p in cat.property_names]

    results = {
        'action':                         'Get',
        'resource':                       'PropertyNameResource',
        'propertiesAvailablePerCategory': categories,
        'message':                        get_message(f"Receiving Property Names from database.")
        }

    return results
