from typing import Dict, Any, List
import numpy as np
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from .base import BaseAgent


class AnswerResult(BaseModel):
    question: str
    user_answer: str
    correct_answer: str
    is_correct: bool
    feedback: str = Field(description="50자 이내")
    score: float = Field(ge=0.0, le=1.0)


class AnswerEvaluation(BaseModel):
    results: List[AnswerResult]
    overall_feedback: str = Field(description="100자 이내 종합 평가")


class EvaluatorAgent(BaseAgent):
    def __init__(self, api_key: str, api_url: str):
        super().__init__("evaluator")
        self.model = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash", google_api_key=api_key, temperature=0.3
        )
        self.rag_model = HuggingFaceEmbeddings(model_name="jhgan/ko-sroberta-multitask")
        self.answer_eval_chain = (
            ChatPromptTemplate.from_template(
                "다음 답안들을 평가하고 종합적인 피드백을 제공해주세요.\n\n"
                "답안들:\n{answers_text}\n\n"
                "평가 기준:\n"
                "1. 답변이 정확히 일치하지 않더라도, 핵심 개념이 맞으면 부분 점수 부여\n"
                "2. 오탈자나 띄어쓰기 차이는 무시\n"
                "3. 객관식의 경우 번호나 내용이 정확히 일치해야 함\n"
                "4. 각 문제의 점수는 0.0 ~ 1.0 사이의 값으로 평가"
            )
            | self.model.with_structured_output(AnswerEvaluation)
        )

    async def execute_function(self, function_name: str, arguments: Dict[str, Any]) -> Any:
        if function_name == "evaluate_answers":
            return await self.evaluate_answers(arguments["answers"])
        elif function_name == "evaluate_single_answer":
            return await self.evaluate_single_answer(arguments["answer"])
        elif function_name == "verify_questions":
            return await self.verify_questions(arguments["questions"], arguments["context"])
        raise ValueError(f"Unknown function: {function_name}")

    async def evaluate_answers(self, answers: List[Dict]) -> Dict:
        try:
            answers_text = "\n".join(
                f"문제 {i+1}:\n질문: {a['question']}\n답변: {a['user_answer']}\n정답: {a['correct_answer']}"
                for i, a in enumerate(answers)
            )

            eval_result = await self.answer_eval_chain.ainvoke({"answers_text": answers_text})

            results = []
            for i, r in enumerate(eval_result.results):
                if i < len(answers):
                    results.append(
                        {
                            "question": r.question or answers[i]["question"],
                            "user_answer": r.user_answer or answers[i]["user_answer"],
                            "correct_answer": r.correct_answer or answers[i]["correct_answer"],
                            "is_correct": r.is_correct,
                            "feedback": r.feedback,
                            "score": max(0.0, min(1.0, r.score)),
                        }
                    )

            total_questions = len(answers)
            total_score = sum(r["score"] for r in results)
            score_percentage = (total_score / total_questions * 100) if total_questions > 0 else 0.0

            return {
                "results": results,
                "total": {
                    "total_score": int(total_score),
                    "total_questions": total_questions,
                    "score_percentage": round(score_percentage, 2),
                    "overall_feedback": eval_result.overall_feedback
                    or f"총 {total_questions}문제 중 {int(total_score)}문제를 맞추었습니다. (정답률: {round(score_percentage, 2)}%)",
                },
            }

        except Exception as e:
            print(f"[ERROR] 답안 평가 중 오류 발생: {str(e)}")
            default_results = [
                {
                    "question": a["question"],
                    "user_answer": a["user_answer"],
                    "correct_answer": a["correct_answer"],
                    "is_correct": False,
                    "feedback": f"평가 오류: {str(e)}",
                    "score": 0.0,
                }
                for a in answers
            ]
            return {
                "results": default_results,
                "total": {
                    "total_score": 0,
                    "total_questions": len(answers),
                    "score_percentage": 0.0,
                    "overall_feedback": f"답안 평가 중 오류가 발생했습니다: {str(e)}",
                },
            }

    async def evaluate_single_answer(self, answer: Dict) -> Dict:
        result = await self.evaluate_answers([answer])
        return (
            result["results"][0]
            if result["results"]
            else {
                "question": answer["question"],
                "user_answer": answer["user_answer"],
                "correct_answer": answer["correct_answer"],
                "is_correct": False,
                "feedback": "평가 중 오류가 발생했습니다.",
                "score": 0.0,
            }
        )

    def get_embedding(self, text: str):
        return np.array(self.rag_model.embed_query(self.preprocess_text(text)))

    def preprocess_text(self, text: str) -> str:
        return " ".join(text.split()).replace("•", "")

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    async def verify_questions(self, questions: List[Dict], context: str) -> Dict:
        try:
            doc_embedding = self.get_embedding(context)
            rag_filtered_questions = []

            for question in questions:
                try:
                    q_embedding = self.get_embedding(question["question"])
                    a_embedding = self.get_embedding(question["correct_answer"])
                    e_embedding = self.get_embedding(question["explanation"])

                    similarities = {
                        "question": self._cosine_similarity(doc_embedding, q_embedding),
                        "answer": self._cosine_similarity(doc_embedding, a_embedding),
                        "explanation": self._cosine_similarity(doc_embedding, e_embedding),
                    }

                    avg_similarity = sum(similarities.values()) / 3
                    if avg_similarity >= 0.4:
                        rag_filtered_questions.append(
                            {**question, "semantic_similarity": avg_similarity}
                        )
                except Exception as e:
                    print(f"[DEBUG] 개별 문제 RAG 검증 중 오류: {str(e)}")
                    continue

            print(f"[DEBUG] RAG 필터링 결과: {len(rag_filtered_questions)}개 통과")
            return {
                "questions": rag_filtered_questions,
                "stats": {
                    "total_generated": len(questions),
                    "rag_filtered": len(rag_filtered_questions),
                    "final_verified": len(rag_filtered_questions),
                },
            }

        except Exception as e:
            print(f"[ERROR] 문제 검증 중 오류: {str(e)}")
            raise
