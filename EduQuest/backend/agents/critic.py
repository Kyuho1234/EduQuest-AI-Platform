from typing import Dict, Any, List
import requests
import os
import json
import re
from .base import BaseAgent


class OpenRouterCriticAgent(BaseAgent):
    def __init__(self, api_key: str,
                 primary_model: str = "deepseek/deepseek-chat-v3-0324:free",
                 secondary_model: str = "qwen/qwen3-235b-a22b:free"):
        super().__init__("critic")
        self.api_key = api_key
        self.primary_model = primary_model
        self.secondary_model = secondary_model
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

    async def execute_function(self, function_name: str, arguments: Dict[str, Any]) -> Any:
        if function_name == "verify_questions":
            return await self.verify_questions(
                questions=arguments["questions"],
                context=arguments["context"]
            )
        raise ValueError(f"Unknown function: {function_name}")

    async def verify_questions(self, questions: List[Dict], context: str) -> List[Dict]:
        """LLM-as-a-judge 방식으로 문제 품질 2중 검증"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "MMS Google Quiz Generator",
            "Content-Type": "application/json"
        }

        verified_questions = []
        for question in questions:
            try:
                # 문제 정보를 더 간단하고 명확하게 표시
                question_info = (
                    f"질문: {question['question']}\n"
                    f"보기: {', '.join(question['options'])}\n"
                    f"정답: {question['correct_answer']}\n"
                    f"해설: {question['explanation']}"
                )

                prompt = f"""주어진 문제가 입력 자료를 정확하게 반영하는지 평가해주세요.

[입력 자료]
{context}

[평가할 문제]
{question_info}

[평가 기준]
1. 입력 자료 참고도: 문제와 답이 입력 자료에 근거하는가?
2. 문제 품질: 문제가 명확하고 적절한가?

반드시 다음 JSON 형식으로만 응답하세요. 다른 텍스트나 설명을 포함하지 마세요:
{{
    "verification": {{
        "reference_check": {{
            "result": "예",
            "evidence": "입력 자료의 구체적인 근거",
            "issues": []
        }},
        "quality_assessment": {{
            "grade": "매우 적절",
            "strengths": ["장점1", "장점2"],
            "weaknesses": [],
            "improvement_suggestions": []
        }},
        "passed": true,
        "feedback": "검토 의견"
    }}
}}"""

                # Primary 모델 검증
                primary_data = {
                    "model": self.primary_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "당신은 교육 분야의 전문가이자 엄격한 평가자입니다. 반드시 지정된 JSON 형식으로만 응답하세요."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.1,
                }

                print(f"\n[DEBUG] Primary 모델 검증 요청:\n{json.dumps(primary_data, indent=2, ensure_ascii=False)}")

                primary_response = requests.post(self.api_url, headers=headers, json=primary_data, timeout=30)
                primary_response.raise_for_status()
                primary_result = primary_response.json()

                print(f"\n[DEBUG] Primary API 응답:\n{json.dumps(primary_result, indent=2, ensure_ascii=False)}")

                primary_verification = None
                if "choices" in primary_result and primary_result["choices"]:
                    content = primary_result["choices"][0]["message"]["content"]
                    if isinstance(content, str):
                        content = content.strip()
                        content = re.sub(r'```json\s*|\s*```', '', content)
                        start = content.find('{')
                        end = content.rfind('}') + 1
                        if start != -1 and end > start:
                            content = content[start:end]
                            try:
                                verification = json.loads(content)
                                if "verification" in verification:
                                    primary_verification = verification["verification"]
                            except json.JSONDecodeError as e:
                                print(f"\n[ERROR] Primary JSON 파싱 오류: {str(e)}")

                # Secondary 모델 검증
                secondary_data = {
                    "model": self.secondary_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "당신은 교육 분야의 전문가이자 엄격한 평가자입니다. 반드시 지정된 JSON 형식으로만 응답하세요."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.1,
                }

                print(f"\n[DEBUG] Secondary 모델 검증 요청:\n{json.dumps(secondary_data, indent=2, ensure_ascii=False)}")

                secondary_response = requests.post(self.api_url, headers=headers, json=secondary_data, timeout=30)
                secondary_response.raise_for_status()
                secondary_result = secondary_response.json()

                print(f"\n[DEBUG] Secondary API 응답:\n{json.dumps(secondary_result, indent=2, ensure_ascii=False)}")

                secondary_verification = None
                if "choices" in secondary_result and secondary_result["choices"]:
                    content = secondary_result["choices"][0]["message"]["content"]
                    if isinstance(content, str):
                        content = content.strip()
                        content = re.sub(r'```json\s*|\s*```', '', content)
                        start = content.find('{')
                        end = content.rfind('}') + 1
                        if start != -1 and end > start:
                            content = content[start:end]
                            try:
                                verification = json.loads(content)
                                if "verification" in verification:
                                    secondary_verification = verification["verification"]
                            except json.JSONDecodeError as e:
                                print(f"\n[ERROR] Secondary JSON 파싱 오류: {str(e)}")

                # 두 모델의 검증 결과 확인 및 통합
                if primary_verification and secondary_verification:
                    # 두 모델 모두 통과한 경우만 최종 통과
                    if primary_verification["passed"] and secondary_verification["passed"]:
                        verified_questions.append({
                            **question,
                            "verification": primary_verification,  # primary 결과를 기본으로 사용
                            "verification_details": {
                                "primary": primary_verification,
                                "secondary": secondary_verification,
                                "dual_verified": True
                            }
                        })
                    else:
                        # 하나라도 실패하면 탈락
                        verified_questions.append({
                            **question,
                            "verification": {
                                "reference_check": {
                                    "result": "아니오",
                                    "evidence": "검증 불일치",
                                    "issues": ["모델 간 검증 결과 불일치"]
                                },
                                "quality_assessment": {
                                    "grade": "부적절",
                                    "strengths": [],
                                    "weaknesses": ["검증 기준 미달"],
                                    "improvement_suggestions": ["문제 재검토 필요"]
                                },
                                "passed": False,
                                "feedback": "두 모델의 검증 결과가 불일치하여 문제가 탈락되었습니다."
                            },
                            "verification_details": {
                                "primary": primary_verification,
                                "secondary": secondary_verification,
                                "dual_verified": False
                            }
                        })
                else:
                    # 검증 실패 시 기본 응답
                    verified_questions.append({
                        **question,
                        "verification": {
                            "reference_check": {
                                "result": "아니오",
                                "evidence": "검증 실패",
                                "issues": ["API 응답 처리 실패"]
                            },
                            "quality_assessment": {
                                "grade": "부적절",
                                "strengths": [],
                                "weaknesses": ["검증 실패"],
                                "improvement_suggestions": []
                            },
                            "passed": False,
                            "feedback": "문제 검증에 실패했습니다."
                        },
                        "verification_details": {
                            "primary": primary_verification,
                            "secondary": secondary_verification,
                            "dual_verified": False
                        }
                    })

            except Exception as e:
                print(f"\n[ERROR] 문제 검증 중 오류: {str(e)}")
                verified_questions.append({
                    **question,
                    "verification": {
                        "reference_check": {
                            "result": "아니오",
                            "evidence": "오류 발생",
                            "issues": [str(e)]
                        },
                        "quality_assessment": {
                            "grade": "부적절",
                            "strengths": [],
                            "weaknesses": ["처리 오류"],
                            "improvement_suggestions": []
                        },
                        "passed": False,
                        "feedback": f"검증 중 오류가 발생했습니다: {str(e)}"
                    }
                })

        return verified_questions