import datetime
import logging

from plants_tagger.models import get_sql_session
from plants_tagger.models.orm_tables import Measurement
from plants_tagger.util.exif_helper import decode_record_date_time

logger = logging.getLogger(__name__)


def update_measurements_from_list_of_dicts(measurements: [dict]):

    new_list = []
    logger.info(f"Updating/Creating {len(measurements)} measurements & events")
    for m in measurements:
        measurement_date_obj = decode_record_date_time(m['measurement_date'])
        measurement_date = measurement_date_obj.strftime('%Y-%m-%d')
        record_update = get_sql_session().query(Measurement).filter_by(plant_name=m['plant_name'],
                                                                       measurement_date=measurement_date).first()
        if record_update:
            boo_new = False
            dict_record = record_update.__dict__.copy()
            del dict_record['_sa_instance_state']
            dict_record['measurement_date'] = m['measurement_date']
            if dict_record == m:
                logger.debug(f'No changes in measurement {m["plant_name"]}/{measurement_date}')
                continue

        else:
            boo_new = True
            if [r for r in new_list if r.plant_name == m['plant_name'] and r.measurement_date == measurement_date]:
                continue  # don't create duplicates
            # create new record (as object) & add to list later)
            record_update = Measurement(plant_name=m['plant_name'],
                                        measurement_date=measurement_date_obj)
            logger.info(f'Saving new measurement {m["plant_name"]}/{measurement_date}')

        # catch key errors (new entries don't have all keys in the dict)
        record_update.repot_rating = m['repot_rating'] if 'repot_rating' in m else None
        # record_update.stem_outset_diameter = m['stem_outset_diameter'] if 'stem_outset_diameter' in m else None
        record_update.stem_max_diameter = m['stem_max_diameter'] if 'stem_max_diameter' in m else None
        record_update.height = m['height'] if 'height' in m else None
        record_update.pot_width_above = m['pot_width_above'] if 'pot_width_above' in m else None
        record_update.pot_width_below = m['pot_width_below'] if 'pot_width_below' in m else None
        record_update.pot_circular = m['pot_circular'] if 'pot_circular' in m else None
        # record_update.pot_height = m['pot_height'] if 'pot_height' in m else None
        record_update.pot_material = m['pot_material'] if 'pot_material' in m else None
        record_update.soil = m['soil'] if 'soil' in m else None
        record_update.notes = m['notes'] if 'notes' in m else None

        record_update.last_update = datetime.datetime.now()

        if boo_new:
            new_list.append(record_update)

    if new_list:
        get_sql_session().add_all(new_list)

    get_sql_session().commit()  # saves changes in existing records, too
