import socket
import sys
import pykew.powo as powo

from plants_tagger.models.taxon_id_mapper import get_gbif_id_from_ipni_id

ip = socket.gethostbyname(socket.gethostname())
if ip.startswith('80.241'):
    print('Server 80.241... detected. Adding path to sys path')
    sys.path.append('/projects/plants/plants_backend')

from plants_tagger.models.orm_tables import Taxon, Distribution
from plants_tagger.models.orm_util import get_sql_session, init_sqlalchemy_engine

init_sqlalchemy_engine()


def add_distribution():
    query = get_sql_session().query(Taxon).all()
    print(len(query))
    for taxon in query:
        print(f'{taxon.name}: {len(taxon.distribution)}')
        if len(taxon.distribution) > 0:
            continue
        powo_lookup = powo.lookup(taxon.fq_id, include=['distribution'])

        dist = []
        if powo_lookup and 'distribution' in powo_lookup and powo_lookup['distribution']:
            # collect native and introduced distribution into one list
            if 'natives' in powo_lookup['distribution']:
                dist.extend(powo_lookup['distribution']['natives'])
            if 'introduced' in powo_lookup['distribution']:
                dist.extend(powo_lookup['distribution']['introduced'])

        if not dist:
            print(f'No distribution info found for {taxon.name}.')
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

            print(f'Found {len(dist)} areas for {taxon.name}.')
            get_sql_session().commit()
            print(f'Added distribution for {taxon.name} in database.')


def add_gbif_id():
    query = get_sql_session().query(Taxon).all()
    print(len(query))
    count = 0
    for taxon in query:
        print(f'Starting {taxon.name}')

        if not taxon.fq_id:
            print(f'no taxon id: {taxon.name}')
            continue

        if taxon.gbif_id:
            print(f'Has already gbif_id: {taxon.gbif_id}')
            continue

        gbif_id = get_gbif_id_from_ipni_id(taxon.fq_id)
        if gbif_id:
            taxon.gbif_id = gbif_id
            print(f'Successfully got gbif_id: {taxon.gbif_id}')
            get_sql_session().commit()
            count += 1
        else:
            print(f'Could not get gbif_id for: {taxon.name}')

    print(f'Finished. Count={count}')


if __name__ == '__main__':
    # add_distribution()
    add_gbif_id()
