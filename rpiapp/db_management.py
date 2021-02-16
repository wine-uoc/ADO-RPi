"""Database management methods from outside flaskapp context."""
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker

from config import ConfigRPI


def check_table_database(engine=None):
    """Check if table userdata exists."""
    if engine:
        exists = engine.dialect.has_table(engine.connect(), "userdata")
    else:
        engine = create_engine(ConfigRPI.DATABASE_URI, echo=False)  # print(engine.table_names())
        exists = engine.dialect.has_table(engine.connect(), "userdata")
    return engine, exists


def get_table_database(engine, table_name):
    """Query first entry from given table name. Returns read-only tuple!"""
    if not engine:
        engine = create_engine(ConfigRPI.DATABASE_URI, echo=False)

    metadata = MetaData(bind=engine)
    metadata.reflect()  # Table reflection
    Session = sessionmaker(bind=engine)     # Session to db
    session = Session()
    table = metadata.tables[table_name]
    query = session.query(table).first()    # Get table (read-only!)
    session.close()
    return query, engine


def update_tokens_table_database(engine, account_token, thing_id, thing_key, channel_id):
    """Reflect table, update given new values and commit."""
    if not engine:
        engine = create_engine(ConfigRPI.DATABASE_URI, echo=False)

    Base = automap_base()   # Ask SQLAlchemy to reflect the tables and create the corresponding ORM classes
    Base.prepare(engine, reflect=True)

    table = Base.classes.tokens     # ORM class we are interested in

    Session = sessionmaker(bind=engine)     # Create the session, query, update and commit
    session = Session()
    table_row = session.query(table).first()
    table_row.account_token = account_token
    table_row.thing_id = thing_id
    table_row.thing_key = thing_key
    table_row.channel_id = channel_id
    session.commit()
    session.close()

def update_calibration_1_table_database(engine, idx_sensor, value):
    """Reflect table, update given new values and commit."""
    if not engine:
        engine = create_engine(ConfigRPI.DATABASE_URI, echo=False)

    Base = automap_base()   # Ask SQLAlchemy to reflect the tables and create the corresponding ORM classes
    Base.prepare(engine, reflect=True)

    table = Base.classes.calibration_1    # ORM class we are interested in

    Session = sessionmaker(bind=engine)     # Create the session, query, update and commit
    session = Session()
    table_row = session.query(table).first()
    if idx_sensor < 10:
        idx_sensor_str = 's0' + str(idx_sensor)
    else:
        idx_sensor_str = 's' + str(idx_sensor)
    setattr(table_row, idx_sensor_str, value)
    # table_row.update({"s08": 11})

    session.commit()
    session.close()

def update_calibration_1_temp_table_database(engine, idx_sensor, value):
    """Reflect table, update given new values and commit."""
    if not engine:
        engine = create_engine(ConfigRPI.DATABASE_URI, echo=False)

    Base = automap_base()   # Ask SQLAlchemy to reflect the tables and create the corresponding ORM classes
    Base.prepare(engine, reflect=True)

    table = Base.classes.calibration_1_temp    # ORM class we are interested in

    Session = sessionmaker(bind=engine)     # Create the session, query, update and commit
    session = Session()
    table_row = session.query(table).first()
    if idx_sensor < 10:
        idx_sensor_str = 's0' + str(idx_sensor)
    else:
        idx_sensor_str = 's' + str(idx_sensor)
    setattr(table_row, idx_sensor_str, value)
    # table_row.update({"s08": 11})

    session.commit()
    session.close()

def update_calibration_2_temp_table_database(engine, idx_sensor, value):
    """Reflect table, update given new values and commit."""
    if not engine:
        engine = create_engine(ConfigRPI.DATABASE_URI, echo=False)

    Base = automap_base()   # Ask SQLAlchemy to reflect the tables and create the corresponding ORM classes
    Base.prepare(engine, reflect=True)

    table = Base.classes.calibration_2_temp    # ORM class we are interested in

    Session = sessionmaker(bind=engine)     # Create the session, query, update and commit
    session = Session()
    table_row = session.query(table).first()
    if idx_sensor < 10:
        idx_sensor_str = 's0' + str(idx_sensor)
    else:
        idx_sensor_str = 's' + str(idx_sensor)
    setattr(table_row, idx_sensor_str, value)
    # table_row.update({"s08": 11})

    session.commit()
    session.close()

def update_calibration_2_table_database(engine, idx_sensor, value):
    """Reflect table, update given new values and commit."""
    if not engine:
        engine = create_engine(ConfigRPI.DATABASE_URI, echo=False)

    Base = automap_base()   # Ask SQLAlchemy to reflect the tables and create the corresponding ORM classes
    Base.prepare(engine, reflect=True)

    table = Base.classes.calibration_2   # ORM class we are interested in

    Session = sessionmaker(bind=engine)     # Create the session, query, update and commit
    session = Session()
    table_row = session.query(table).first()
    if idx_sensor < 10:
        idx_sensor_str = 's0' + str(idx_sensor)
    else:
        idx_sensor_str = 's' + str(idx_sensor)
    setattr(table_row, idx_sensor_str, value)
    # table_row.update({"s08": 11})

    session.commit()
    session.close()


def update_nodeconfig_table_database(engine, idx_sensor, value):
    """Reflect table, update given new values and commit."""
    if not engine:
        engine = create_engine(ConfigRPI.DATABASE_URI, echo=False)

    Base = automap_base()   # Ask SQLAlchemy to reflect the tables and create the corresponding ORM classes
    Base.prepare(engine, reflect=True)

    table = Base.classes.nodeconfig     # ORM class we are interested in

    Session = sessionmaker(bind=engine)     # Create the session, query, update and commit
    session = Session()
    table_row = session.query(table).first()

    if idx_sensor < 10:
        idx_sensor_str = 's0' + str(idx_sensor)
    else:
        idx_sensor_str = 's' + str(idx_sensor)
    setattr(table_row, idx_sensor_str, value)
    # table_row.update({"s08": 11})
    session.commit()
    session.close()

def update_req_cal_1_table_database(engine, idx_sensor, value):
    """Reflect table, update given new values and commit."""
    if not engine:
        engine = create_engine(ConfigRPI.DATABASE_URI, echo=False)

    Base = automap_base()   # Ask SQLAlchemy to reflect the tables and create the corresponding ORM classes
    Base.prepare(engine, reflect=True)

    table = Base.classes.req_cal_1     # ORM class we are interested in

    Session = sessionmaker(bind=engine)     # Create the session, query, update and commit
    session = Session()
    table_row = session.query(table).first()

    if idx_sensor < 10:
        idx_sensor_str = 's0' + str(idx_sensor)
    else:
        idx_sensor_str = 's' + str(idx_sensor)
    setattr(table_row, idx_sensor_str, value)
    # table_row.update({"s08": 11})
    session.commit()
    session.close()

def update_req_cal_2_table_database(engine, idx_sensor, value):
    """Reflect table, update given new values and commit."""
    if not engine:
        engine = create_engine(ConfigRPI.DATABASE_URI, echo=False)

    Base = automap_base()   # Ask SQLAlchemy to reflect the tables and create the corresponding ORM classes
    Base.prepare(engine, reflect=True)

    table = Base.classes.req_cal_2    # ORM class we are interested in

    Session = sessionmaker(bind=engine)     # Create the session, query, update and commit
    session = Session()
    table_row = session.query(table).first()

    if idx_sensor < 10:
        idx_sensor_str = 's0' + str(idx_sensor)
    else:
        idx_sensor_str = 's' + str(idx_sensor)
    setattr(table_row, idx_sensor_str, value)
    # table_row.update({"s08": 11})
    session.commit()
    session.close()