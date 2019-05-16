from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

import settings

if __name__ == 'database':
    engine = create_engine(settings.DB_URI, echo=True)
    session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
    Base = declarative_base()
    from database.models import Benign, RawFile, User, BitDefender, Kaspersky, Kisa, Symantec ,\
    Virusshare, Virussign

    Base.metadata.create_all(engine)
    session.commit()
