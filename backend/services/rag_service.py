import os
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
import torch
from typing import List, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from pgvector.sqlalchemy.utils import cosine_distance
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 환경 변수 로드
API_KEY = os.getenv("GOOGLE_API_KEY")
DB_URL = os.getenv("DB1_URL", "postgresql://db1_user:db1_pass@localhost:5432/db1_database")

# Gemini 모델 설정
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# RAG 모델 설정
rag_model = SentenceTransformer('jhgan/ko-sroberta-multitask')

# DB 연결 설정
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_embedding(text: str):
    """텍스트에서 임베딩 계산"""
    return rag_model.encode(text, convert_to_tensor=True).tolist()

def preprocess_text(text: str) -> str:
    """텍스트 전처리"""
    return ' '.join(text.split()).replace('•', '')

async def retrieve_relevant_chunks(question: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """문제와 유사한 청크 검색"""
    try:
        # DB 세션 생성
        db = SessionLocal()
        
        # 질문 임베딩 계산
        embedding = get_embedding(preprocess_text(question))
        
        # 유사한 청크 검색
        query = """
        SELECT chunk_text, document_id, 
               1 - COSINE_DISTANCE(embedding, :embedding) AS similarity
        FROM document_chunks
        ORDER BY COSINE_DISTANCE(embedding, :embedding) ASC
        LIMIT :limit
        """
        
        result = db.execute(query, {
            "embedding": embedding, 
            "limit": top_k
        })
        
        # 결과 가공
        chunks = []
        for row in result:
            chunks.append({
                "text": row[0],
                "document_id": row[1],
                "similarity": float(row[2])
            })
        
        # 세션 종료
        db.close()
        
        return chunks
    
    except Exception as e:
        logger.error(f"청크 검색 중 오류 발생: {str(e)}")
        return []

async def answer_with_rag(question: str) -> str:
    """RAG 기반 답변 생성"""
    try:
        # 관련 청크 검색
        chunks = await retrieve_relevant_chunks(question)
        
        if not chunks:
            return "관련 정보를 찾을 수 없습니다."
        
        # 컨텍스트 구성
        context = "\n\n".join([chunk["text"] for chunk in chunks])
        
        # 프롬프트 생성
        prompt = f"""아래 주어진 컨텍스트를 바탕으로 질문에 답변해주세요.
        
컨텍스트:
{context}

질문: {question}

지침:
1. 컨텍스트에 있는 정보만 사용하여 답변하세요.
2. 컨텍스트에 답이 없으면 "해당 질문에 대한 정보가 컨텍스트에 없습니다"라고 답하세요.
3. 답변은 명확하고 직접적으로 제공하세요.
4. 필요한 경우 주어진 정보를 논리적으로 연결하여 추론할 수 있습니다.
"""
        
        # Gemini로 답변 생성
        response = model.generate_content(prompt)
        
        return response.text
    
    except Exception as e:
        logger.error(f"RAG 답변 생성 중 오류: {str(e)}")
        return f"답변 생성 중 오류가 발생했습니다: {str(e)}"