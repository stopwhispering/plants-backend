import logging
import socket
import sys
import pykew.powo as powo

ip = socket.gethostbyname(socket.gethostname())
if ip.startswith('80.241'):
    logging.getLogger().warning('Server 80.241... detected. Adding path to sys path')
    sys.path.append('/projects/plants/plants_backend')

from plants_tagger.models.orm_tables import Taxon, Distribution
from plants_tagger.models.orm_util import get_sql_session, init_sqlalchemy_engine

init_sqlalchemy_engine()
logger = logging.getLogger(__name__)


def add_distribution():
    query = get_sql_session().query(Taxon).filter(Taxon.distribution == None).all()
    for taxon in query:
        powo_lookup = powo.lookup(taxon.fq_id, include=['distribution'])

        dist = []
        if powo_lookup and 'distribution' in powo_lookup and powo_lookup['distribution']:
            # collect native and introduced distribution into one list
            if 'natives' in powo_lookup['distribution']:
                dist.extend(powo_lookup['distribution']['natives'])
            if 'introduced' in powo_lookup['distribution']:
                dist.extend(powo_lookup['distribution']['introduced'])

        if not dist:
            logger.info(f'No distribution info found for {taxon.name}.')
        else:
            # new_records = []
            for area in dist:
                record = Distribution(name=area.get('name'),
                                      establishment=area.get('establishment'),
                                      feature_id=area.get('featureId'),
                                      tdwg_code=area.get('tdwgCode'),
                                      tdwg_level=area.get('tdwgLevel')
                                      )
                # new_records.append(record)
                taxon.distribution.append(record)

            logger.info(f'Found {len(dist)} areas for {taxon.name}.')
            get_sql_session().commit()
            logger.info(f'Added distribution for {taxon.name} in database.')


add_distribution()
