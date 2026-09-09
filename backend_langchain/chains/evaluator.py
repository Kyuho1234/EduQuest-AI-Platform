import numpy as np
from langchain_core.prompts import ChatPromptTemplate
from config import embeddings, gemini, GROUNDING_THRESHOLD
from schemas import Question, AnswerEvaluation


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    a, b = (np.array(a), np.array(b))
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def check_grounding(question: Question, document_text: str) -> dict:
    doc_embedding = embeddings.embed_query(document_text)
    q_embedding = embeddings.embed_query(question.question)
    a_embedding = embeddings.embed_query(question.correct_answer)
    e_embedding = embeddings.embed_query(question.explanation)
    similarities = {
        "question": _cosine_similarity(doc_embedding, q_embedding),
        "answer": _cosine_similarity(doc_embedding, a_embedding),
        "explanation": _cosine_similarity(doc_embedding, e_embedding),
    }
    avg_similarity = sum(similarities.values()) / 3
    return {
        "question": question,
        "grounded": avg_similarity >= GROUNDING_THRESHOLD,
        "similarity": avg_similarity,
        "similarity_breakdown": similarities,
    }


answer_eval_prompt = ChatPromptTemplate.from_template(
    "다음 답안들을 평가하고 종합적인 피드백을 제공해주세요.\n\n답안들:\n{answers_text}\n\n평가 기준:\n1. 답변이 정확히 일치하지 않더라도, 핵심 개념이 맞으면 부분 점수 부여\n2. 오탈자나 띄어쓰기 차이는 무시\n3. 객관식의 경우 번호나 내용이 정확히 일치해야 함\n4. 각 문제의 점수는 0.0 ~ 1.0 사이의 값으로 평가"
)
answer_eval_chain = answer_eval_prompt | gemini.with_structured_output(AnswerEvaluation)


async def evaluate_answers(answers: list[dict]) -> AnswerEvaluation:
    answers_text = "\n".join(
        (
            f"문제 {i + 1}:\n질문: {a['question']}\n답변: {a['user_answer']}\n정답: {a['correct_answer']}"
            for i, a in enumerate(answers)
        )
    )
    return await answer_eval_chain.ainvoke({"answers_text": answers_text})
