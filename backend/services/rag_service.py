import os
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
from sqlalchemy import select
from db.db1 import SessionDB1
from models.vector_doc import VectorDocument

model = SentenceTransformer("jhgan/ko-sroberta-multitask")

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-2.0-pro")


async def find_similar_contexts(question: str, top_k: int = 3):
    """DB1에서 질문과 가장 유사한 context top_k개 찾기 (pgvector 인덱스 기반 DB 레벨 검색)"""
    q_vec = model.encode(question).tolist()

    async with SessionDB1() as session:
        stmt = (
            select(VectorDocument)
            .order_by(VectorDocument.embedding.cosine_distance(q_vec))
            .limit(top_k)
        )
        result = await session.execute(stmt)
        docs = result.scalars().all()

    return [doc.content for doc in docs]


async def answer_with_rag(question: str):
    """RAG를 이용해 질문에 답변 생성"""
    contexts = await find_similar_contexts(question)
    if not contexts:
        return "관련 문맥을 찾을 수 없습니다."

    prompt = "\n\n".join(contexts) + f"\n\n질문: {question}\n답변:"
    try:
        response = gemini_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"[ERROR] Gemini 응답 실패: {str(e)}")
        return "답변 생성에 실패했습니다."
