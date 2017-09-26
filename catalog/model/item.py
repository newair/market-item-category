from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from base import *


class Item(Base):

    def __init__(self, name, description, cat_id, user_id):
        self.name = name
        self.description = description
        self.user_id = user_id
        self.cat_id = cat_id

    __tablename__ = 'items'
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("user.id"))
    cat_id = Column(Integer, ForeignKey("categories.id"))
    name = Column(String)
    description = Column(Text)
    category = relationship("Category", back_populates="items")

    @property
    def serialize(self):
        # serialized item data
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'cat_id': self.cat_id
        }
