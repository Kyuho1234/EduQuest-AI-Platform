import os
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
from sqlalchemy import select
from db.db1 import SessionDB1
from models.document_chunk import DocumentChunk

model = SentenceTransformer("jhgan/ko-sroberta-multitask")

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-2.0-pro")


async def find_similar_contexts(question: str, document_id: str = None, user_id: str = None, top_k: int = 3):
    """
    업로드 플로우(/api/upload-pdf)가 실제로 채워 넣는 document_chunks 테이블에서
    질문과 가장 유사한 청크 top_k개를 DB 레벨에서 검색.

    document_id를 주면 해당 문서 안에서만 검색하고, 주지 않으면
    (user_id가 있다면 그 사용자의) 모든 업로드 문서를 대상으로 검색한다.
    """
    q_vec = model.encode(question).tolist()

    async with SessionDB1() as session:
        conditions = []
        if document_id is not None:
            conditions.append(DocumentChunk.document_id == document_id)
        if user_id is not None:
            conditions.append(DocumentChunk.user_id == user_id)

        stmt = select(DocumentChunk).order_by(DocumentChunk.embedding.cosine_distance(q_vec)).limit(top_k)
        if conditions:
            stmt = stmt.where(*conditions)

        result = await session.execute(stmt)
        chunks = result.scalars().all()

    return [chunk.chunk_text for chunk in chunks]


async def answer_with_rag(question: str, document_id: str = None, user_id: str = None):
    """RAG를 이용해 질문에 답변 생성 (실제 업로드된 문서 청크를 검색 대상으로 사용)"""
    contexts = await find_similar_contexts(question, document_id=document_id, user_id=user_id)
    if not contexts:
        return "관련 문맥을 찾을 수 없습니다."

    prompt = "\n\n".join(contexts) + f"\n\n질문: {question}\n답변:"
    try:
        response = gemini_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"[ERROR] Gemini 응답 실패: {str(e)}")
        return "답변 생성에 실패했습니다."
