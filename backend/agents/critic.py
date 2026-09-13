from typing import Dict, Any, List
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableParallel
from .base import BaseAgent
from services.routing_service import get_routing_decision


class CriticVerdict(BaseModel):
    passed: bool
    reference_check_result: str = Field(description="'예' 또는 '아니오'")
    reference_evidence: str
    quality_grade: str = Field(description="예: '매우 적절', '적절', '부적절'")
    feedback: str


class OpenRouterCriticAgent(BaseAgent):
    def __init__(
        self,
        api_key: str,
        primary_model: str = "deepseek/deepseek-chat-v3-0324:free",
        secondary_model: str = "qwen/qwen3-235b-a22b:free",
    ):
        super().__init__("critic")
        headers = {
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "MMS Google Quiz Generator",
        }
        self.primary_llm = ChatOpenAI(
            model=primary_model,
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            temperature=0.1,
            default_headers=headers,
        )
        self.secondary_llm = ChatOpenAI(
            model=secondary_model,
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            temperature=0.1,
            default_headers=headers,
        )

        self.critic_prompt = ChatPromptTemplate.from_template(
            "주어진 문제가 입력 자료를 정확하게 반영하는지 평가해주세요.\n\n"
            "[입력 자료]\n{context}\n\n"
            "[평가할 문제]\n질문: {question}\n보기: {options}\n정답: {correct_answer}\n해설: {explanation}\n\n"
            "[평가 기준]\n"
            "1. 입력 자료 참고도: 문제와 답이 입력 자료에 근거하는가?\n"
            "2. 문제 품질: 문제가 명확하고 적절한가?\n\n"
            "당신은 교육 분야의 전문가이자 엄격한 평가자입니다."
        )

        self.primary_chain = self.critic_prompt | self.primary_llm.with_structured_output(CriticVerdict)
        self.secondary_chain = self.critic_prompt | self.secondary_llm.with_structured_output(CriticVerdict)

        # 무거운 경로: 두 모델을 동시에 호출해서 교차 검증
        self.dual_chain = RunnableParallel(
            primary=self.primary_chain,
            secondary=self.secondary_chain,
        )

    async def execute_function(self, function_name: str, arguments: Dict[str, Any]) -> Any:
        if function_name == "verify_questions":
            return await self.verify_questions(
                questions=arguments["questions"],
                context=arguments["context"],
                user_id=arguments.get("user_id"),
            )
        raise ValueError(f"Unknown function: {function_name}")

    async def verify_questions(self, questions: List[Dict], context: str, user_id: str = None) -> List[Dict]:
        verified_questions = []

        for question in questions:
            try:
                inputs = {
                    "context": context,
                    "question": question["question"],
                    "options": ", ".join(question["options"]),
                    "correct_answer": question["correct_answer"],
                    "explanation": question["explanation"],
                }

                # 벡터 DB 유사도 기반 동적 라우팅:
                # 이미 검증 통과한 과거 문제와 유사도가 높으면(light) 단일 모델만으로 검증하고,
                # 새로운 유형이거나 유사도가 낮으면(heavy) 기존처럼 이중 모델 교차 검증을 거친다.
                routing = await get_routing_decision(question["question"], user_id)

                if routing["route"] == "light":
                    primary: CriticVerdict = await self.primary_chain.ainvoke(inputs)
                    dual_verified = primary.passed
                    secondary_dump = None
                else:
                    result = await self.dual_chain.ainvoke(inputs)
                    primary: CriticVerdict = result["primary"]
                    secondary: CriticVerdict = result["secondary"]
                    dual_verified = primary.passed and secondary.passed
                    secondary_dump = secondary.model_dump()

                if dual_verified:
                    verification = {
                        "reference_check": {
                            "result": primary.reference_check_result,
                            "evidence": primary.reference_evidence,
                            "issues": [],
                        },
                        "quality_assessment": {
                            "grade": primary.quality_grade,
                            "strengths": [],
                            "weaknesses": [],
                            "improvement_suggestions": [],
                        },
                        "passed": True,
                        "feedback": primary.feedback,
                    }
                else:
                    verification = {
                        "reference_check": {
                            "result": "아니오",
                            "evidence": "검증 불일치",
                            "issues": ["모델 간 검증 결과 불일치"] if routing["route"] == "heavy" else ["단일 모델 검증 실패"],
                        },
                        "quality_assessment": {
                            "grade": "부적절",
                            "strengths": [],
                            "weaknesses": ["검증 기준 미달"],
                            "improvement_suggestions": ["문제 재검토 필요"],
                        },
                        "passed": False,
                        "feedback": "검증 기준을 통과하지 못해 문제가 탈락되었습니다.",
                    }

                verified_questions.append(
                    {
                        **question,
                        "verification": verification,
                        "verification_details": {
                            "primary": primary.model_dump(),
                            "secondary": secondary_dump,
                            "dual_verified": dual_verified,
                        },
                        "routing": routing,
                    }
                )

            except Exception as e:
                print(f"문제 검증 중 오류: {str(e)}")
                verified_questions.append(
                    {
                        **question,
                        "verification": {
                            "reference_check": {
                                "result": "아니오",
                                "evidence": "오류 발생",
                                "issues": [str(e)],
                            },
                            "quality_assessment": {
                                "grade": "부적절",
                                "strengths": [],
                                "weaknesses": ["처리 오류"],
                                "improvement_suggestions": [],
                            },
                            "passed": False,
                            "feedback": f"검증 중 오류가 발생했습니다: {str(e)}",
                        },
                        "routing": {"route": "heavy", "reason": "오류로 인한 기본값", "similarity": None},
                    }
                )

        return verified_questions
