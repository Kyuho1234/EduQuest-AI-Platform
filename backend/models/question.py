from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    question = Column(Text)
    correct_answer = Column(Text)
    explanation = Column(Text)
    options = Column(JSONB, nullable=True)
    type = Column(String)
    document_name = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    embedding = Column(Vector(768), nullable=True)
