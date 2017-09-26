from catalog.model.base import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from model.item import Item
from model.category import Category


engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.create_all(engine)

DBSession = sessionmaker(bind=engine)
session = DBSession()
