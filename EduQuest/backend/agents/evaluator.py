from typing import Dict, Any, List
import google.generativeai as genai
import json
from .base import BaseAgent
import re
from sentence_transformers import SentenceTransformer
import torch

class EvaluatorAgent(BaseAgent):
    def __init__(self, api_key: str, api_url: str):
        super().__init__("evaluator")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        # RAG 모델 초기화
        self.rag_model = SentenceTransformer('jhgan/ko-sroberta-multitask')
    
    async def execute_function(self, function_name: str, arguments: Dict[str, Any]) -> Any:
        if function_name == "evaluate_answers":
            return await self.evaluate_answers(arguments["answers"])
        elif function_name == "evaluate_single_answer":
            return await self.evaluate_single_answer(arguments["answer"])
        elif function_name == "verify_questions":
            return await self.verify_questions(arguments["questions"], arguments["context"])
        raise ValueError(f"Unknown function: {function_name}")
    
    async def evaluate_answers(self, answers: List[Dict]) -> Dict:
        """여러 답안을 한 번에 평가"""
        try:
            answers_text = "\n".join([
                f"문제 {i+1}:\n질문: {answer['question']}\n답변: {answer['user_answer']}\n정답: {answer['correct_answer']}"
                for i, answer in enumerate(answers)
            ])
            
            prompt = f"""다음 답안들을 평가하고 종합적인 피드백을 제공해주세요.

답안들:
{answers_text}

반드시 다음 JSON 형식으로만 응답하세요. 다른 텍스트나 설명을 포함하지 마세요:
{{
    "results": [
        {{
            "question": "문제 내용",
            "user_answer": "제출한 답안",
            "correct_answer": "정답",
            "is_correct": true/false,
            "feedback": "개별 피드백 (50자 이내)",
            "score": 1.0
        }}
    ],
    "total": {{
        "total_score": 0,
        "total_questions": {len(answers)},
        "score_percentage": 0.0,
        "overall_feedback": "종합 평가 (100자 이내)"
    }}
}}

평가 기준:
1. 답변이 정확히 일치하지 않더라도, 핵심 개념이 맞으면 부분 점수 부여
2. 오탈자나 띄어쓰기 차이는 무시
3. 객관식의 경우 번호나 내용이 정확히 일치해야 함
4. 각 문제의 점수는 0.0 ~ 1.0 사이의 값으로 평가
5. 총점은 각 문제의 점수 합계이며, 백분율은 (총점 / 문제 수 * 100)으로 계산"""

            response = self.model.generate_content(prompt)
            json_str = response.text
            
            # JSON 문자열 정제
            if isinstance(json_str, str):
                # 코드 블록 제거
                json_str = re.sub(r'```json\s*|\s*```', '', json_str)
                json_str = re.sub(r'```\s*|\s*```', '', json_str)
                
                # JSON 시작/끝 위치 찾기
                start = json_str.find('{')
                end = json_str.rfind('}') + 1
                
                if start != -1 and end > start:
                    json_str = json_str[start:end]
                    print(f"\n[DEBUG] 정제된 JSON 문자열:\n{json_str}")
                    
                    result = json.loads(json_str)
                    
                    # 결과 검증 및 보정
                    if "results" not in result or not isinstance(result["results"], list):
                        # 결과가 없거나 잘못된 형식인 경우 기본 응답 생성
                        result["results"] = []
                        for answer in answers:
                            result["results"].append({
                                "question": answer["question"],
                                "user_answer": answer["user_answer"],
                                "correct_answer": answer["correct_answer"],
                                "is_correct": False,
                                "feedback": "평가 실패",
                                "score": 0.0
                            })
                    
                    # 각 결과에 필수 필드가 있는지 확인하고 보정
                    for i, res in enumerate(result["results"]):
                        if i < len(answers):  # 원본 답안이 있는 경우에만
                            res["question"] = res.get("question", answers[i]["question"])
                            res["user_answer"] = res.get("user_answer", answers[i]["user_answer"])
                            res["correct_answer"] = res.get("correct_answer", answers[i]["correct_answer"])
                            res["is_correct"] = res.get("is_correct", False)
                            res["feedback"] = res.get("feedback", "평가 실패")
                            # score를 float으로 변환하고 0~1 범위로 제한
                            try:
                                score = float(res.get("score", 0.0))
                                res["score"] = max(0.0, min(1.0, score))  # 0~1 범위로 제한
                            except (ValueError, TypeError):
                                res["score"] = 0.0
                    
                    # total 정보 계산 및 보정
                    total_questions = len(answers)
                    if total_questions > 0:
                        # 각 문제의 점수를 합산 (0~1 범위의 점수)
                        total_score = sum(r.get("score", 0.0) for r in result["results"])
                        # 백분율 계산 (0~100 범위)
                        score_percentage = (total_score / total_questions) * 100
                    else:
                        total_score = 0
                        score_percentage = 0
                    
                    # 점수 정보를 정수로 변환하여 저장
                    result["total"] = {
                        "total_score": int(total_score),  # 맞은 문제 수
                        "total_questions": total_questions,
                        "score_percentage": round(score_percentage, 2),  # 소수점 2자리까지 표시
                        "overall_feedback": result.get("total", {}).get("overall_feedback", 
                            f"총 {total_questions}문제 중 {int(total_score)}문제를 맞추었습니다. (정답률: {round(score_percentage, 2)}%)")
                    }
                    
                    print(f"[DEBUG] 점수 계산 결과: 총점={total_score}, 문제수={total_questions}, 백분율={score_percentage}%")
                    return result
                    
            # 응답 파싱 실패 시 기본 응답 생성
            default_results = []
            for answer in answers:
                default_results.append({
                    "question": answer["question"],
                    "user_answer": answer["user_answer"],
                    "correct_answer": answer["correct_answer"],
                    "is_correct": False,
                    "feedback": "답안 평가 중 오류가 발생했습니다.",
                    "score": 0.0
                })
            
            return {
                "results": default_results,
                "total": {
                    "total_score": 0,
                    "total_questions": len(answers),
                    "score_percentage": 0.0,
                    "overall_feedback": "답안 평가 중 오류가 발생했습니다."
                }
            }
            
        except Exception as e:
            print(f"[ERROR] 답안 평가 중 오류 발생: {str(e)}")
            # 오류 발생 시 기본 응답 생성
            default_results = []
            for answer in answers:
                default_results.append({
                    "question": answer["question"],
                    "user_answer": answer["user_answer"],
                    "correct_answer": answer["correct_answer"],
                    "is_correct": False,
                    "feedback": f"평가 오류: {str(e)}",
                    "score": 0.0
                })
            
            return {
                "results": default_results,
                "total": {
                    "total_score": 0,
                    "total_questions": len(answers),
                    "score_percentage": 0.0,
                    "overall_feedback": f"답안 평가 중 오류가 발생했습니다: {str(e)}"
                }
            }
    
    async def evaluate_single_answer(self, answer: Dict) -> Dict:
        """단일 답안 평가"""
        result = await self.evaluate_answers([answer])
        return result["results"][0] if result["results"] else {
            "question": answer["question"],
            "user_answer": answer["user_answer"],
            "correct_answer": answer["correct_answer"],
            "is_correct": False,
            "feedback": "평가 중 오류가 발생했습니다.",
            "score": 0.0
        }

    def get_embedding(self, text: str):
        """임베딩 결과 계산"""
        return self.rag_model.encode(self.preprocess_text(text), convert_to_tensor=True)

    def preprocess_text(self, text: str) -> str:
        """텍스트 전처리"""
        return ' '.join(text.split()).replace('•', '')

    async def verify_questions(self, questions: List[Dict], context: str) -> Dict:
        """RAG와 Critic을 통합한 문제 검증 프로세스"""
        try:
            # 1. RAG 기반 1차 필터링
            doc_embedding = self.get_embedding(context)
            rag_filtered_questions = []
            
            for question in questions:
                try:
                    # 임베딩 계산
                    q_embedding = self.get_embedding(question["question"])
                    a_embedding = self.get_embedding(question["correct_answer"])
                    e_embedding = self.get_embedding(question["explanation"])
                    
                    # 유사도 계산
                    similarities = {
                        "question": float(torch.cosine_similarity(doc_embedding.unsqueeze(0), q_embedding.unsqueeze(0))),
                        "answer": float(torch.cosine_similarity(doc_embedding.unsqueeze(0), a_embedding.unsqueeze(0))),
                        "explanation": float(torch.cosine_similarity(doc_embedding.unsqueeze(0), e_embedding.unsqueeze(0)))
                    }
                    
                    avg_similarity = sum(similarities.values()) / 3
                    if avg_similarity >= 0.4:  # 1차 필터링 임계값
                        rag_filtered_questions.append({
                            **question,
                            "semantic_similarity": avg_similarity
                        })
                except Exception as e:
                    print(f"[DEBUG] 개별 문제 RAG 검증 중 오류: {str(e)}")
                    continue
            
            print(f"[DEBUG] RAG 필터링 결과: {len(rag_filtered_questions)}개 통과")
            
            # 2. 문제 품질 검증
            if rag_filtered_questions:
                prompt = f"""다음 문제들이 주어진 컨텍스트에 기반하여 적절한지 검증해주세요.

컨텍스트:
{context}

문제들:
{json.dumps(rag_filtered_questions, ensure_ascii=False, indent=2)}

다음 형식으로 JSON 응답을 작성해주세요:
{{
    "questions": [
        {{
            "question": "문제 내용",
            "options": ["보기1", "보기2", "보기3", "보기4"],
            "correct_answer": "정답",
            "explanation": "해설",
            "verification": {{
                "is_valid": true/false,
                "feedback": "검증 피드백",
                "confidence": 0.95
            }}
        }}
    ],
    "stats": {{
        "total_reviewed": 3,
        "valid_count": 2,
        "average_confidence": 0.85
    }}
}}"""

                response = self.model.generate_content(prompt)
                verification_result = json.loads(response.text)
                
                # 검증 결과 처리
                final_questions = []
                for q in verification_result["questions"]:
                    if q["verification"]["is_valid"]:
                        # RAG 유사도 점수 찾기
                        rag_score = next(
                            (rq["semantic_similarity"] for rq in rag_filtered_questions 
                             if rq["question"] == q["question"]),
                            0.0
                        )
                        # 최종 신뢰도 점수 계산
                        final_confidence = (rag_score + q["verification"]["confidence"]) / 2
                        final_questions.append({
                            **q,
                            "final_confidence": final_confidence
                        })
                
                # 최종 신뢰도 기준으로 정렬
                final_questions.sort(key=lambda x: x.get("final_confidence", 0), reverse=True)
                
                result = {
                    "questions": final_questions,
                    "stats": {
                        "total_generated": len(questions),
                        "rag_filtered": len(rag_filtered_questions),
                        "final_verified": len(final_questions)
                    }
                }
                
                print(f"[DEBUG] 최종 검증 결과: {json.dumps(result, ensure_ascii=False, indent=2)}")
                return result
            
            return {
                "questions": [],
                "stats": {
                    "total_generated": len(questions),
                    "rag_filtered": 0,
                    "final_verified": 0
                }
            }
            
        except Exception as e:
            print(f"[ERROR] 문제 검증 중 오류: {str(e)}")
            raise 