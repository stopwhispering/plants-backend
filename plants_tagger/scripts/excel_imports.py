# import pandas as pd
# from sqlalchemy.exc import IntegrityError
# import math
# import logging
# import socket
# import sys
#
# ip = socket.gethostbyname(socket.gethostname())
# if ip.startswith('80.241'):
#     logging.getLogger().warning('Server 80.241... detected. Adding path to sys path')
#     sys.path.append('/projects/plants/plants_backend')
#
# from plants_tagger.config_local import FILE_PATH_BOTANICA_XLSX
# from plants_tagger.models.orm_tables import Botany, Plant, Measurement
# from plants_tagger.models.orm_util import get_sql_session, init_sqlalchemy_engine
#
# init_sqlalchemy_engine()
# logger = logging.getLogger(__name__)
#
#
# def import_botany_from_xlsx_to_db():
#     df = pd.read_excel(FILE_PATH_BOTANICA_XLSX, sheet_name=2)
#     for index, row in df.iterrows():
#         b = get_sql_session().query(Botany).filter(Botany.species == row['Art_species']).first()
#         if not b:
#             b = Botany()
#             new = True
#         else:
#             new = False
#         b.species = row['Art_species']
#         b.description = row['deutsch_syn_description']
#         b.subgenus = row['Untergattung_subgenus']
#         b.genus = row['Gattung_genus']
#         b.subfamilia = row['Unterfamilie_subfamilia']
#         b.familia = row['Familie_familia']
#         b.ordo = row['Ordnung_ordo']
#         b.subclassis = row['Unterklasse_subclassis']
#         b.classis = row['Klasse_classis']
#         b.divisio = row['Abteilung_divisio']
#         b.superdivisio = row['Überabteilung_superdivisio']
#         b.subregnum = row['Unterreich_subregnum']
#         b.notes = row['Kommentar']
#         if new:
#             get_sql_session().add(b)
#             logger.info(f'inserted: {b.species}')
#         else:
#             logger.info(f'updated: {b.species}')
#         try:
#             get_sql_session().commit()
#         except IntegrityError:
#             logger.info(f'skipped (already existing): {b.species}')
#             get_sql_session().rollback()
#
#
# def is_nan_or_none(x):
#     if not x:
#         return True
#     elif type(x) is float and math.isnan(x):
#         return True
#     else:
#         return False
#
#
# import_botany_from_xlsx_to_db()
