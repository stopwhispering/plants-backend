from plants.extensions import orm


def get_db():
    db = orm.SessionFactory.create_session()
    try:
        yield db
    finally:
        db.close()
