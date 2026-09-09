from typing import Dict, Any, List
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from .base import BaseAgent
from PyPDF2 import PdfReader
from fastapi import UploadFile


class Concept(BaseModel):
    concept: str = Field(description="핵심 개념")
    description: str = Field(description="개념 설명")
    importance: float = Field(ge=0.0, le=1.0)


class ConceptList(BaseModel):
    concepts: List[Concept]


class Question(BaseModel):
    type: str = "multiple_choice"
    question: str
    options: List[str] = Field(min_length=4, max_length=4)
    correct_answer: str
    explanation: str
    evidence: str
    concept: str
    difficulty: float = Field(ge=0.0, le=1.0)


class QuestionList(BaseModel):
    questions: List[Question]


class QuestionGeneratorAgent(BaseAgent):
    def __init__(self, api_key: str):
        super().__init__("question_generator")
        self.model = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash", google_api_key=api_key, temperature=0.7
        )
        self.concept_chain = (
            ChatPromptTemplate.from_template(
                "다음 텍스트에서 핵심 개념들을 추출해주세요.\n\n텍스트:\n{text}\n\n"
                "각 개념의 이름, 설명, 중요도(0.0~1.0)를 포함해주세요."
            )
            | self.model.with_structured_output(ConceptList)
        )
        self.question_chain = (
            ChatPromptTemplate.from_template(
                "다음 핵심 개념들을 바탕으로 문제를 생성해주세요.\n\n"
                "핵심 개념:\n{concepts}\n\n원본 텍스트:\n{text}\n\n"
                "다음 지침을 엄격히 따라주세요:\n"
                "1. 정확히 3개의 객관식 문제를 생성하세요.\n"
                "2. 각 문제는 반드시 텍스트 내용과 추출된 핵심 개념에 기반해야 합니다.\n"
                "3. 각 문제는 4개의 보기를 가져야 합니다.\n"
                "4. 정답은 반드시 보기 중 하나여야 합니다.\n"
                "5. 해설은 왜 그 답이 정답인지 명확히 설명해야 합니다.\n"
                "6. 각 문제의 난이도는 개념의 중요도를 반영해야 합니다.\n"
                "7. 표나 그림을 참조하는 문제는 내지 마세요."
            )
            | self.model.with_structured_output(QuestionList)
        )

    async def execute_function(self, function_name: str, arguments: Dict[str, Any]) -> Any:
        if function_name == "generate_questions":
            return await self.generate_questions(arguments["text"])
        elif function_name == "extract_text":
            return await self.extract_text(arguments["file"])
        raise ValueError(f"Unknown function: {function_name}")

    async def extract_text(self, file: UploadFile) -> str:
        pdf = PdfReader(file.file)
        text = ""
        for page in pdf.pages:
            text += page.extract_text()
        return self.preprocess_text(text)

    def preprocess_text(self, text: str) -> str:
        return " ".join(text.split()).replace("•", "")

    async def generate_questions(self, text: str) -> List[Dict]:
        try:
            concepts = await self.concept_chain.ainvoke({"text": text})
            result = await self.question_chain.ainvoke(
                {"concepts": concepts.model_dump_json(), "text": text}
            )

            validated_questions = []
            for q in result.questions:
                if self._validate_question(q):
                    validated_questions.append(q.model_dump())

            if not validated_questions:
                raise ValueError("유효한 문제가 생성되지 않았습니다")

            return validated_questions

        except Exception as e:
            print(f"문제 생성 중 오류 발생: {str(e)}")
            return []

    def _validate_question(self, question: Question) -> bool:
        try:
            if question.type != "multiple_choice":
                return False
            if len(question.options) != 4:
                return False
            if question.correct_answer not in question.options:
                return False
            if not question.question.strip() or not question.explanation.strip():
                return False
            return True
        except Exception as e:
            print(f"문제 검증 중 오류: {str(e)}")
            return False
