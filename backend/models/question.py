from sqlalchemy import Column, Integer, Text, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    correct_answer = Column(Text, nullable=False)
    explanation = Column(Text)
    metadata = Column(JSON)  # (검증 결과, 생성 정보 등 저장용)