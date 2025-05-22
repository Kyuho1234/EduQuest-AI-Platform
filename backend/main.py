from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
import torch
from PyPDF2 import PdfReader
import os
from dotenv import load_dotenv
from typing import List, Dict
import json
import re
from functools import lru_cache
from services.rag_service import answer_with_rag
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import JSONB
from collections import defaultdict
from uuid import uuid4

# A2A 에이전트 import
from agents.question_generator import QuestionGeneratorAgent
from agents.critic import OpenRouterCriticAgent
from agents.evaluator import EvaluatorAgent

load_dotenv()

#검증AI api키 확인
USE_CRITIC = bool(os.getenv("OPENROUTER_API_KEY"))

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 문서 벡터DB 연결 정보
DB1_URL = os.getenv("DB1_URL", "postgresql://db1_user:db1_pass@localhost:5432/db1_database")
engine_db1 = create_engine(DB1_URL)
SessionDB1 = sessionmaker(autocommit=False, autoflush=False, bind=engine_db1)

# 문제 DB 연결 정보
DB2_URL = os.getenv("DB2_URL", "postgresql://db2_user:db2_pass@localhost:5432/db2_database")
engine_db2 = create_engine(DB2_URL)
SessionDB2 = sessionmaker(autocommit=False, autoflush=False, bind=engine_db2)

BaseDB1 = declarative_base()
BaseDB2 = declarative_base()

#문서 메타 정보
class Document(BaseDB1):
    __tablename__ = "documents"
    id = Column(String, primary_key=True)  # UUID
    user_id = Column(String)
    filename = Column(String)
    created_at = Column(DateTime, server_default=func.now())

#문서 청크 + 임베딩 저장
class DocumentChunk(BaseDB1):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True)
    user_id = Column(String)
    document_id = Column(String)
    chunk_text = Column(Text)
    embedding = Column(Vector(768))  # SentenceTransformer 출력 차원
    created_at = Column(DateTime, server_default=func.now())

class Question(BaseDB2):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    question = Column(Text)
    correct_answer = Column(Text)
    explanation = Column(Text)
    options = Column(JSONB, nullable=True)
    type = Column(String)
    created_at = Column(DateTime, server_default=func.now())

BaseDB1.metadata.create_all(bind=engine_db1)
BaseDB2.metadata.create_all(bind=engine_db2)


def get_vector_db():
    db = SessionDB1()
    try:
        yield db
    finally:
        db.close()
def get_db():
    db = SessionDB2()
    try:
        yield db
    finally:
        db.close()

@app.post("/api/rag-answer")
async def rag_answer(data: Dict):
    """
    질문을 받아 RAG 기반으로 답변 생성
    """
    try:
        question = data.get("question")
        if not question:
            raise HTTPException(status_code=400, detail="question 필드가 필요합니다.")

        answer = await answer_with_rag(question)
        return {
            "success": True,
            "question": question,
            "answer": answer
        }
    except Exception as e:
        print(f"[ERROR] RAG 답변 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="RAG 답변 생성 중 오류가 발생했습니다.")

# Gemini 모델 설정
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash')

# RAG 모델 설정
rag_model = SentenceTransformer('jhgan/ko-sroberta-multitask')

# 에이전트 초기화
question_generator = QuestionGeneratorAgent(api_key=os.getenv("GOOGLE_API_KEY"))
critic = OpenRouterCriticAgent(api_key=os.getenv("OPENROUTER_API_KEY"))
evaluator = EvaluatorAgent(
    api_key=os.getenv("GOOGLE_API_KEY"),
    api_url="https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash"
)

@lru_cache(maxsize=100)
def get_embedding(text: str):
    """임베딩 결과를 캐시하여 재사용"""
    return rag_model.encode(preprocess_text(text), convert_to_tensor=True)

def preprocess_text(text: str) -> str:
    return ' '.join(text.split()).replace('•', '')

def extract_text_from_pdf(file: UploadFile) -> str:
    pdf = PdfReader(file.file)
    text = ""
    for page in pdf.pages:
        text += page.extract_text()
    return preprocess_text(text)

def create_overlapping_chunks(text: str, chunk_size: int = 450, overlap: int = 100) -> List[str]:
    """오버랩이 있는 청크 생성
    Args:
        text (str): 원본 텍스트
        chunk_size (int): 청크 최대 크기 (토큰 기준, 기본값 450으로 버퍼 확보)
        overlap (int): 청크 간 오버랩 크기
    Returns:
        List[str]: 청크 리스트
    """
    sentences = re.split('[.!?]', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    chunks = []
    current_chunk = []
    current_length = 0
    
    for sentence in sentences:
        sentence_length = len(sentence.split())
        
        if current_length + sentence_length <= chunk_size:
            current_chunk.append(sentence)
            current_length += sentence_length
        else:
            # 현재 청크 저장
            if current_chunk:
                chunks.append('. '.join(current_chunk) + '.')
            
            # 오버랩 처리
            if overlap > 0 and current_chunk:
                # 마지막 몇 개의 문장을 새로운 청크의 시작으로 사용
                overlap_sentences = current_chunk[-(overlap//20):]  # 대략적인 문장 수 계산
                current_chunk = overlap_sentences.copy()  # copy로 참조 문제 방지
                current_length = sum(len(s.split()) for s in overlap_sentences)
            else:
                current_chunk = []
                current_length = 0
            
            current_chunk.append(sentence)
            current_length = sentence_length
    
    if current_chunk:
        chunks.append('. '.join(current_chunk) + '.')
    
    return chunks

async def verify_questions_with_rag_and_critic(questions: List[Dict], context: str) -> Dict:
    """RAG와 Critic을 통합한 효율적인 검증 프로세스"""
    try:
        # 1. RAG 기반 1차 필터링
        doc_embedding = get_embedding(context)
        rag_filtered_questions = []
        
        for question in questions:
            try:
                # 임베딩 계산
                q_embedding = get_embedding(question["question"])
                a_embedding = get_embedding(question["correct_answer"])
                e_embedding = get_embedding(question["explanation"])
                
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
                print(f"[ERROR] 개별 문제 RAG 검증 중 오류: {str(e)}")
                continue
        
        print(f"[INFO] RAG 필터링 결과: {len(rag_filtered_questions)}/{len(questions)}개 통과")
        
        # 2. LLM 검증 (OpenRouter Critic 모델 사용)
        if USE_CRITIC and rag_filtered_questions:
            # 에이전트 메시지 생성
            agent_message = {
                "function_call": {
                    "name": "verify_questions",
                    "arguments": {
                        "questions": rag_filtered_questions,
                        "context": context
                    }
                }
            }
            
            # 에이전트에 요청 전송
            critic_response = await critic.process_message(agent_message)
            
            if critic_response.get("status") == "success" and critic_response.get("content"):
                verified_by_critic = critic_response.get("content")
                print(f"[INFO] Critic 검증 결과: {len(verified_by_critic)}개 검증 완료")
                
                # 통과한 문제만 필터링
                verified_questions = [q for q in verified_by_critic if q.get("verification", {}).get("passed", False)]
                
                # 신뢰도 점수 기준으로 정렬
                for q in verified_questions:
                    q["reliability_score"] = q.get("semantic_similarity", 0.0)
                
                verified_questions.sort(key=lambda x: x.get("reliability_score", 0), reverse=True)
                print(f"[INFO] 최종 통과 문제: {len(verified_questions)}개")
                
                # 최대 5개만 반환
                return {"verified_questions": verified_questions[:5]}
            
        # Critic 사용 불가능하거나 실패 시 RAG 결과만 반환
        # 신뢰도 점수 기준으로 정렬
        for q in rag_filtered_questions:
            q["reliability_score"] = q.get("semantic_similarity", 0.0)
        
        rag_filtered_questions.sort(key=lambda x: x.get("reliability_score", 0), reverse=True)
        
        # 최대 5개만 반환
        return {"verified_questions": rag_filtered_questions[:5]}
    
    except Exception as e:
        print(f"[ERROR] 문제 검증 중 오류 발생: {str(e)}")
        return {"verified_questions": []}

def get_text_by_document_id(document_id: str, db: Session) -> str:
    """문서 ID로 전체 텍스트 가져오기"""
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).all()
    if not chunks:
        return ""
    return " ".join([chunk.chunk_text for chunk in chunks])

@app.post("/api/generate-questions-from-document")
async def generate_questions_from_document(data: Dict, db: Session = Depends(get_vector_db), user_db: Session = Depends(get_db)):
    """
    문서 ID로 문제 생성
    """
    try:
        document_id = data.get("document_id")
        user_id = data.get("user_id")
        
        if not document_id or not user_id:
            raise HTTPException(status_code=400, detail="document_id와 user_id가 필요합니다.")

        # 문서 존재 여부 확인
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
        
        # 문서 텍스트 가져오기
        text = get_text_by_document_id(document_id, db)
        if not text:
            raise HTTPException(status_code=404, detail="문서 내용을 찾을 수 없습니다.")
        
        # 텍스트 길이 제한 (필요시)
        if len(text) > 8000:
            text = text[:8000]
        
        # 에이전트에 문제 생성 요청
        agent_message = {
            "function_call": {
                "name": "generate_questions",
                "arguments": {
                    "text": text
                }
            }
        }
        response = await question_generator.process_message(agent_message)
        
        if response.get("status") == "success" and response.get("content"):
            questions = response.get("content")
            
            # 문제 검증
            verification_result = await verify_questions_with_rag_and_critic(questions, text)
            verified_questions = verification_result.get("verified_questions", [])
            
            # 검증된 문제가 없으면 원본 반환
            if not verified_questions and questions:
                verified_questions = questions[:3]  # 최대 3개만 반환
            
            return {
                "success": True,
                "document_id": document_id,
                "document_title": document.filename,
                "questions": verified_questions
            }
        else:
            return {
                "success": False,
                "message": "문제 생성에 실패했습니다."
            }
    
    except Exception as e:
        print(f"[ERROR] 문서 기반 문제 생성 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"문제 생성 중 오류가 발생했습니다: {str(e)}")

@app.post("/api/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    db: Session = Depends(get_vector_db)
):
    """
    PDF 파일 업로드 및 임베딩 저장
    """
    try:
        # 파일 확장자 확인
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="PDF 파일만 업로드할 수 있습니다.")
        
        # 텍스트 추출
        text = extract_text_from_pdf(file)
        
        # 문서 ID 생성
        document_id = str(uuid4())
        
        # 문서 메타데이터 저장
        document = Document(
            id=document_id,
            user_id=user_id,
            filename=file.filename
        )
        db.add(document)
        
        # 청크 생성 및 임베딩 저장
        chunks = create_overlapping_chunks(text)
        for chunk_text in chunks:
            embedding = get_embedding(chunk_text).cpu().numpy().tolist()
            chunk = DocumentChunk(
                user_id=user_id,
                document_id=document_id,
                chunk_text=chunk_text,
                embedding=embedding
            )
            db.add(chunk)
        
        db.commit()
        
        return {
            "success": True,
            "document_id": document_id,
            "filename": file.filename,
            "chunks": len(chunks)
        }
    
    except Exception as e:
        db.rollback()
        print(f"[ERROR] PDF 업로드 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PDF 처리 중 오류가 발생했습니다: {str(e)}")

@app.get("/api/documents/{user_id}")
def list_documents(user_id: str, db: Session = Depends(get_vector_db)):
    """사용자별 문서 목록 조회"""
    documents = db.query(Document).filter(Document.user_id == user_id).all()
    return {
        "success": True,
        "documents": [{"id": doc.id, "filename": doc.filename, "created_at": doc.created_at} for doc in documents]
    }

@app.post("/api/check-answers")
async def check_answers(data: Dict):
    """
    답안 채점 및 피드백 제공
    """
    try:
        answers = data.get("answers")
        if not answers or not isinstance(answers, list):
            raise HTTPException(status_code=400, detail="answers 필드가 필요합니다.")
        
        # 필수 필드 검증
        for i, answer in enumerate(answers):
            if not all(k in answer for k in ["question", "user_answer", "correct_answer"]):
                return {
                    "success": False,
                    "message": f"답안 {i+1}에 필수 필드가 누락되었습니다."
                }
        
        # 에이전트에 평가 요청
        agent_message = {
            "function_call": {
                "name": "evaluate_answers",
                "arguments": {
                    "answers": answers
                }
            }
        }
        
        response = await evaluator.process_message(agent_message)
        
        if response.get("status") == "success" and response.get("content"):
            evaluation = response.get("content")
            
            # 결과 구성
            return {
                "success": True,
                "evaluation": evaluation
            }
        else:
            print(f"[ERROR] 평가 실패: {response}")
            return {
                "success": False,
                "message": "답안 평가에 실패했습니다."
            }
    
    except Exception as e:
        print(f"[ERROR] 답안 평가 중 오류: {str(e)}")
        return {
            "success": False,
            "message": f"답안 평가 중 오류가 발생했습니다: {str(e)}"
        }

@app.post("/api/check-answer")
async def check_answer(data: Dict):
    """
    단일 답안 채점 및 피드백 제공
    """
    try:
        answer = data.get("answer")
        if not answer or not isinstance(answer, dict):
            raise HTTPException(status_code=400, detail="answer 필드가 필요합니다.")
        
        # 필수 필드 검증
        if not all(k in answer for k in ["question", "user_answer", "correct_answer"]):
            return {
                "success": False,
                "message": "답안에 필수 필드가 누락되었습니다."
            }
        
        # 에이전트에 평가 요청
        agent_message = {
            "function_call": {
                "name": "evaluate_single_answer",
                "arguments": {
                    "answer": answer
                }
            }
        }
        
        response = await evaluator.process_message(agent_message)
        
        if response.get("status") == "success" and response.get("content"):
            evaluation = response.get("content")
            
            # 결과 구성
            return {
                "success": True,
                "evaluation": evaluation
            }
        else:
            print(f"[ERROR] 평가 실패: {response}")
            return {
                "success": False,
                "message": "답안 평가에 실패했습니다."
            }
    
    except Exception as e:
        print(f"[ERROR] 답안 평가 중 오류: {str(e)}")
        return {
            "success": False,
            "message": f"답안 평가 중 오류가 발생했습니다: {str(e)}"
        }

def safe_json_loads(text: str) -> Dict:
    """JSON 로딩 안전하게 처리"""
    try:
        # 문자열 정제
        if isinstance(text, str):
            # 코드 블록 제거
            text = re.sub(r'```json\s*|\s*```', '', text)
            text = re.sub(r'```\s*|\s*```', '', text)
            
            # JSON 시작/끝 위치 찾기
            start = text.find('{')
            end = text.rfind('}') + 1
            
            if start != -1 and end > start:
                text = text[start:end]
                
                # 이스케이프 문자 처리
                text = text.replace('\\"', '"')
                
                return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    return {}

class QuestionItem(BaseModel):
    question: str
    correct_answer: str
    explanation: str
    options: List[str] = []
    type: str

class SaveQuestionsRequest(BaseModel):
    user_id: str
    questions: List[QuestionItem]

@app.post("/api/save-questions")
async def save_questions(data: SaveQuestionsRequest, db: Session = Depends(get_db)):
    """사용자 문제 저장"""
    try:
        for q in data.questions:
            question = Question(
                user_id=data.user_id,
                question=q.question,
                correct_answer=q.correct_answer,
                explanation=q.explanation,
                options=q.options,
                type=q.type
            )
            db.add(question)
        db.commit()
        return {
            "success": True,
            "message": f"{len(data.questions)}개 문제가 저장되었습니다."
        }
    except Exception as e:
        db.rollback()
        print(f"[ERROR] 문제 저장 중 오류: {str(e)}")
        return {
            "success": False,
            "message": f"문제 저장 중 오류가 발생했습니다: {str(e)}"
        }

@app.get("/api/get-questions/{user_id}")
async def get_questions(user_id: str, db: Session = Depends(get_db)):
    """사용자 문제 목록 조회"""
    try:
        questions = db.query(Question).filter(Question.user_id == user_id).all()
        
        question_list = []
        for q in questions:
            question_list.append({
                "id": q.id,
                "question": q.question,
                "correct_answer": q.correct_answer,
                "explanation": q.explanation,
                "options": q.options if q.options else [],
                "type": q.type,
                "created_at": q.created_at.isoformat()
            })
        
        return {
            "success": True,
            "questions": question_list
        }
    except Exception as e:
        print(f"[ERROR] 문제 조회 중 오류: {str(e)}")
        return {
            "success": False,
            "message": f"문제 조회 중 오류가 발생했습니다: {str(e)}"
        }

@app.post("/api/generate-questions")
async def generate_questions_from_context(data: Dict, db: Session = Depends(get_db)):
    """
    문맥 기반 문제 생성
    """
    try:
        text = data.get("text")
        user_id = data.get("user_id")
        
        if not text:
            raise HTTPException(status_code=400, detail="text 필드가 필요합니다.")
        
        # 텍스트 길이 제한 (필요시)
        if len(text) > 8000:
            text = text[:8000]
        
        # 에이전트에 문제 생성 요청
        agent_message = {
            "function_call": {
                "name": "generate_questions",
                "arguments": {
                    "text": text
                }
            }
        }
        response = await question_generator.process_message(agent_message)
        
        if response.get("status") == "success" and response.get("content"):
            questions = response.get("content")
            
            # 문제 검증
            verification_result = await verify_questions_with_rag_and_critic(questions, text)
            verified_questions = verification_result.get("verified_questions", [])
            
            # 검증된 문제가 없으면 원본 반환
            if not verified_questions and questions:
                verified_questions = questions[:3]  # 최대 3개만 반환
            
            return {
                "success": True,
                "questions": verified_questions
            }
        else:
            return {
                "success": False,
                "message": "문제 생성에 실패했습니다."
            }
    
    except Exception as e:
        print(f"[ERROR] 문제 생성 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"문제 생성 중 오류가 발생했습니다: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)