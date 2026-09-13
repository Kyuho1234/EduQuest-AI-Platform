from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True)
    user_id = Column(String)
    document_id = Column(String)
    chunk_text = Column(Text)
    embedding = Column(Vector(768))
    created_at = Column(DateTime, server_default=func.now())
