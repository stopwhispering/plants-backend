import pandas as pd
# from sqlite3 import IntegrityError
from sqlalchemy.exc import IntegrityError
import datetime
import math
import logging

from plants_tagger.config_local import PATH_BOTANICA_XLSX
from plants_tagger.models.orm_tables import Botany, Plant, Measurement
from plants_tagger.models.orm_util import get_sql_session, init_sqlalchemy_engine

init_sqlalchemy_engine()
logger = logging.getLogger(__name__)

import socket
print(socket.gethostbyname(socket.gethostname()))
print(socket.gethostname())


# PATH = r'C:\temp\pflanzen_temp.xlsx'
# PATH_BOTANIK = r'C:\IDEs\sap-webide-personal-edition-1.53.5-trial\serverworkspace\my\myuser\OrionContent\plants_tagger\webapp\localService\Botanik.xlsx'


def import_botany_from_xlsx_to_db():
    df = pd.read_excel(PATH_BOTANICA_XLSX, sheet_name=2)
    for index, row in df.iterrows():
        b = get_sql_session().query(Botany).filter(Botany.species == row['Art_species']).first()
        if not b:
            b = Botany()
            new = True
        else:
            new = False
        b.species = row['Art_species']
        b.description = row['deutsch_syn_description']
        b.subgenus = row['Untergattung_subgenus']
        b.genus = row['Gattung_genus']
        b.subfamilia = row['Unterfamilie_subfamilia']
        b.familia = row['Familie_familia']
        b.ordo = row['Ordnung_ordo']
        b.subclassis = row['Unterklasse_subclassis']
        b.classis = row['Klasse_classis']
        b.divisio = row['Abteilung_divisio']
        b.superdivisio = row['Überabteilung_superdivisio']
        b.subregnum = row['Unterreich_subregnum']
        b.notes = row['Kommentar']
        if new:
            get_sql_session().add(b)
            logger.info(f'inserted: {b.species}')
        else:
            logger.info(f'updated: {b.species}')
        try:
            get_sql_session().commit()
        except IntegrityError:
            logger.info(f'skipped (already existing): {b.species}')
            get_sql_session().rollback()


def is_nan_or_none(x):
    if not x:
        return True
    elif type(x) is float and math.isnan(x):
        return True
    else:
        return False


# def import_plants_from_xlsx_to_db():
#     df = pd.read_excel(PATH, sheet_name=0)
#     for index, row in df.iterrows():
#         plant = Plant()
#         plant.plant_name = str(row[1]) if not is_nan_or_none(row[1]) else None
#
#         plant.species = str(row[4]) if not is_nan_or_none(row[4]) else None
#         plant.generation_origin = str(row[5]) if not is_nan_or_none(row[5]) else None
#
#         try:
#             s = row[6]
#             d = datetime.date(s[:4], s[5:7], s[8:10])
#             plant.generation_date = d
#         except TypeError:
#             pass
#
#         plant.generation_type = str(row[7]) if not is_nan_or_none(row[7]) else None
#         plant.generation_notes = str(row[8]) if not is_nan_or_none(row[8]) else None
#         # plant.mother_plant = row[9]  todo
#         plant.count = row[10]
#         plant.dead = True if not is_nan_or_none(row[11]) else None
#         plant.plant_notes = str(row[12]) if not is_nan_or_none(row[12]) else None
#         plant.active = False if not is_nan_or_none(row[15]) else None
#
#         plant.last_update = datetime.datetime.now()
#
#         get_sql_session().add(plant)
#         try:
#             get_sql_session().commit()
#             logger.info(f'inserted: {plant.plant_name}')
#         except IntegrityError:
#             logger.info(f'skipped (already existing): {plant.plant_name}')
#             get_sql_session().rollback()
#
#     # add mother plant (constraint requires mother plant to exist before)
#     for index, row in df.iterrows():
#         if not is_nan_or_none(row[9]):
#             plant = get_sql_session().query(Plant).filter(Plant.plant_name == row[1]).first()
#             if not plant:
#                 logger.info('error')
#                 continue
#             plant.mother_plant = str(row[9])
#             try:
#                 get_sql_session().commit()
#                 logger.info(f'inserted mother plant: {plant.plant_name} / {plant.mother_plant}')
#             except IntegrityError:
#                 logger.info(f'skipped (problem inserting mother plant): {plant.plant_name} / {plant.mother_plant}')
#                 get_sql_session().rollback()


# def import_measurements_from_xlsx_to_db():
#     df = pd.read_excel(PATH_BOTANIK, sheet_name=3)
#
#     # check if plant exists for each row
#     not_found = []
#     for index, row in df.iterrows():
#         plant_name = row['Pflanze']
#         p = get_sql_session().query(Plant).filter(Plant.plant_name == plant_name).first()
#         if not p:
#             not_found.append(plant_name)
#     if not_found:
#         raise Exception('Plant(s) not found)')
#
#     # insert into db
#     for index, row in df.iterrows():
#
#         # date must have obj format: to save it,
#         # but s'YYYY-MM-DD to query'
#         # date_byte = b'2019-03-16 00:00:00"'  # see update function
#         # date_obj = decode_record_date_time(date_byte)
#         date_obj = datetime.date(2019,3,16)
#         date_s = date_obj.strftime('%Y-%m-%d')
#
#         m = get_sql_session().query(Measurement).filter(Measurement.plant_name == row['Pflanze'],
#                                                         Measurement.measurement_date == date_s).first()
#         if not m:
#             m = Measurement(plant_name=row['Pflanze'],
#                             measurement_date=date_obj)
#             new = True
#         else:
#             new = False
#
#         m.repot_rating = row['repot_rating']
#         m.stem_outset_diameter = row['stem_outset_diameter']
#         m.stem_max_diameter = row['stem_max_diameter']
#         m.height = row['height']
#         m.pot_width_above = row['pot_width_above']
#         m.pot_circular = row['pot_circular']
#         m.pot_height = row['pot_height']
#         m.pot_material = row['pot_material']
#         m.soil = row['soil']
#         m.notes = row['notes']
#
#         if new:
#             get_sql_session().add(m)
#         try:
#             get_sql_session().commit()
#             logger.info(f'inserted/updated: {m.plant_name} / {m.measurement_date}')
#         except IntegrityError:
#             logger.info(f'Integrity Error')
#             get_sql_session().rollback()


import_botany_from_xlsx_to_db()
# import_plants_from_xlsx_to_db()
# import_measurements_from_xlsx_to_db()