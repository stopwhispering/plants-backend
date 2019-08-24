import pandas as pd
# from sqlite3 import IntegrityError
from sqlalchemy.exc import IntegrityError
import datetime
import math

from plants_tagger.models.orm_tables import Botany, Plant, Measurement
from plants_tagger.models.orm_util import get_sql_session, init_sqlalchemy_engine

init_sqlalchemy_engine()


def do():
    m = Measurement()
    m.plant_name = 'EuphBupl1'
    m.measurement_date = datetime.date(2010,11,11) #datetime.date.today()

    m.repot_rating = 3

    m.stem_max_diameter = 12
    # m.stem_outset_diameter
    m.height = 750

    m.pot_width_above = 51
    m.pot_width_below = 40
    m.pot_height = 60
    m.pot_circular = True
    m.pot_material = 'Plastik'

    m.soil = 'Blumenerde'
    m.notes = 'Hinweise......'

    get_sql_session().add(m)
    get_sql_session().commit()


    m = Measurement()
    m.plant_name = 'EuphBupl1'
    m.measurement_date = datetime.date.today()

    m.repot_rating = 0

    # m.stem_max_diameter = 12
    m.stem_outset_diameter = 89
    # m.height = 122

    m.pot_width_above = 51
    m.pot_width_below = 40
    m.pot_height = 60
    m.pot_circular = False
    m.pot_material = 'Terrakotta'

    get_sql_session().add(m)
    get_sql_session().commit()
    #

do()