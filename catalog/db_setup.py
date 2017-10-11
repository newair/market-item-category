# This file will contain logic in order to setup database.
#  Session variable is exposed globally
from catalog.model.base import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.create_all(engine)

DBSession = sessionmaker(bind=engine)
session = DBSession()
