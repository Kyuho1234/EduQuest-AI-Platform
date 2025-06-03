from sqlalchemy import Column, Integer, Text, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class VectorDocument(Base):
    __tablename__ = "vector_documents"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(Text, nullable=False)  # 임베딩을 JSON 문자열로 저장
