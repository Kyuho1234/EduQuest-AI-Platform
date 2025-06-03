import json
import torch
from db.db1 import SessionDB1
from models.vector_doc import VectorDocument
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
import os

# 모델 로드
model = SentenceTransformer('jhgan/ko-sroberta-multitask')

# Gemini API 설정
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel('gemini-2.0-pro')

async def find_similar_contexts(question: str, top_k: int = 3):
    """DB1에서 질문과 가장 유사한 context top_k개 찾기"""
    q_vec = model.encode(question)
    results = []

    async with SessionDB1() as session:
        docs = await session.execute(
            VectorDocument.__table__.select()
        )
        docs = docs.scalars().all()

        for doc in docs:
            try:
                doc_vec = json.loads(doc.embedding)
                similarity = torch.cosine_similarity(
                    torch.tensor(q_vec).unsqueeze(0),
                    torch.tensor(doc_vec).unsqueeze(0)
                ).item()
                results.append((similarity, doc.content))
            except Exception as e:
                print(f"[ERROR] 벡터 비교 실패: {str(e)}")
                continue

    results.sort(key=lambda x: x[0], reverse=True)
    top_contexts = [r[1] for r in results[:top_k]]
    return top_contexts

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
