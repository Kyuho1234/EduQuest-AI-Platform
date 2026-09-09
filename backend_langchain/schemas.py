from typing import List
from pydantic import BaseModel, Field


class Concept(BaseModel):
    concept: str = Field(description="핵심 개념")
    description: str = Field(description="개념 설명")
    importance: float = Field(description="0.0~1.0 사이의 중요도", ge=0.0, le=1.0)


class ConceptList(BaseModel):
    concepts: List[Concept]


class Question(BaseModel):
    type: str = Field(default="multiple_choice")
    question: str = Field(description="문제 내용")
    options: List[str] = Field(
        description="정확히 4개의 보기", min_length=4, max_length=4
    )
    correct_answer: str = Field(
        description="정답 - 반드시 options 중 하나와 정확히 일치"
    )
    explanation: str = Field(description="해설")
    evidence: str = Field(description="텍스트 내 근거가 되는 부분")
    concept: str = Field(description="관련된 핵심 개념")
    difficulty: float = Field(description="0.0~1.0 사이의 난이도", ge=0.0, le=1.0)


class QuestionList(BaseModel):
    questions: List[Question]


class CriticVerdict(BaseModel):
    passed: bool
    reference_check_result: str = Field(description="'예' 또는 '아니오'")
    evidence: str
    grade: str = Field(description="문제 품질 등급 (예: '매우 적절', '부적절')")
    feedback: str


class AnswerResult(BaseModel):
    question: str
    user_answer: str
    correct_answer: str
    is_correct: bool
    feedback: str = Field(description="개별 피드백, 50자 이내")
    score: float = Field(ge=0.0, le=1.0)


class AnswerEvaluation(BaseModel):
    results: List[AnswerResult]
    total_score: float
    score_percentage: float
    overall_feedback: str
