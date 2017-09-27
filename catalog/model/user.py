from sqlalchemy import Column, Integer, String, Text, ForeignKey
from base import Base


class User(Base):

    def __init__(self, id, email, name, image):
        self.id = id
        self.email = email
        self.name = name
        self.image = image

    __tablename__ = 'user'
    id = Column(String, primary_key=True)
    email = Column(String, nullable=True)
    name = Column(String, nullable=False)
    image = Column(String)
