from sqlalchemy import Column, Integer, String

from database import Base


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    path = Column(String, nullable=False, unique=True)
    title = Column(String, nullable=False)
    content = Column(String, nullable=True)