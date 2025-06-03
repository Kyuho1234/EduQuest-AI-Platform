from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
import torch
from PyPDF2 import PdfReader
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
import os

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
DB1_URL = "postgresql://db1_user:db1_pass@113.198.66.75:13229/db1_database"
engine_db1 = create_engine(DB1_URL)
SessionDB1 = sessionmaker(autocommit=False, autoflush=False, bind=engine_db1)

# 문제 DB 연결 정보
DB2_URL = "postgresql://db2_user:db2_pass@113.198.66.75:10229/db2_database"
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
    document_name = Column(String)
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
        # 1. 텍스트를 청크로 분할
        chunks = create_overlapping_chunks(context)
        print(f"[DEBUG] 청크 생성 결과: {len(chunks)}개 청크 생성됨")
        
        # 2. RAG 기반 1차 필터링
        rag_filtered_questions = []
        
        for question in questions:
            try:
                # 각 청크별로 유사도 계산
                chunk_similarities = []
                for chunk in chunks:
                    try:
                        # 청크에 대한 임베딩 계산
                        chunk_embedding = get_embedding(chunk)
                        q_embedding = get_embedding(question["question"])
                        a_embedding = get_embedding(question["correct_answer"])
                        e_embedding = get_embedding(question["explanation"])
                        
                        # 유사도 계산
                        similarities = {
                            "question": float(torch.cosine_similarity(chunk_embedding.unsqueeze(0), q_embedding.unsqueeze(0))),
                            "answer": float(torch.cosine_similarity(chunk_embedding.unsqueeze(0), a_embedding.unsqueeze(0))),
                            "explanation": float(torch.cosine_similarity(chunk_embedding.unsqueeze(0), e_embedding.unsqueeze(0)))
                        }
                        
                        chunk_similarities.append(similarities)
                    except Exception as e:
                        print(f"[DEBUG] 청크 처리 중 오류: {str(e)}")
                        continue
                
                if chunk_similarities:
                    # 각 청크별 최대 유사도 사용
                    max_similarities = {
                        "question": max(s["question"] for s in chunk_similarities),
                        "answer": max(s["answer"] for s in chunk_similarities),
                        "explanation": max(s["explanation"] for s in chunk_similarities)
                    }
                    
                    # 가중치 적용한 최종 유사도
                    weighted_similarity = (
                        max_similarities["question"] * 0.4 +
                        max_similarities["answer"] * 0.4 +
                        max_similarities["explanation"] * 0.2
                    )
                    
                    if weighted_similarity >= 0.35:  # 임계값 낮춤
                        rag_filtered_questions.append({
                            **question,
                            "semantic_similarity": weighted_similarity,
                            "max_similarities": max_similarities
                        })
            except Exception as e:
                print(f"[DEBUG] 개별 문제 RAG 검증 중 오류: {str(e)}")
                continue
        
        print(f"[DEBUG] RAG 필터링 결과: {len(rag_filtered_questions)}개 통과")
        
        # 3. Critic 기반 2차 검증 (RAG로 필터링된 문제만)
        if not rag_filtered_questions:  # RAG 필터링 결과가 없으면 원본 질문 사용
            print("[DEBUG] RAG 필터링 결과가 없어 원본 질문으로 진행")
            rag_filtered_questions = questions[:5]  # 부하 방지를 위해 최대 5개만

        # 검증ai api키 없을 시 바로 반환
        if not USE_CRITIC:
            print("[DEBUG] OPENROUTER_API_KEY가 없어 Critic 검증을 생략합니다.")
            return {
                "questions": rag_filtered_questions,
                "stats": {
                    "total_generated": len(questions),
                    "rag_filtered": len(rag_filtered_questions),
                    "final_verified": len(rag_filtered_questions)
                }
            }

        # 4. Critic 기반 2차 검증 (RAG로 필터링된 문제만)
        if rag_filtered_questions:
            verification_message = {
                "role": "user",
                "function_call": {
                    "name": "verify_questions",
                    "arguments": {
                        "questions": rag_filtered_questions,
                        "context": context
                    }
                }
            }
            critic_result = await critic.process_message(verification_message)
            print(f"[DEBUG] Critic 응답: {json.dumps(critic_result, ensure_ascii=False, indent=2)}")
            
            try:
                verified_content = safe_json_loads(critic_result["content"]) if isinstance(critic_result["content"], str) else critic_result["content"]
                
                # Critic 검증 결과와 RAG 유사도 점수를 결합
                final_questions = []
                for q in verified_content:
                    try:
                        if q.get("verification", {}).get("passed", False):
                            # RAG 유사도 점수 찾기
                            rag_score = next(
                                (rq["semantic_similarity"] for rq in rag_filtered_questions 
                                 if rq["question"] == q["question"]),
                                0.0
                            )
                            # 최종 신뢰도 점수 계산 (RAG와 Critic 결과 결합)
                            final_confidence = (rag_score + float(q["verification"]["quality_assessment"]["grade"] == "매우 적절")) / 2
                            final_questions.append({
                                **q,
                                "final_confidence": final_confidence
                            })
                    except Exception as e:
                        print(f"[DEBUG] 개별 문제 최종 검증 중 오류: {str(e)}")
                        continue
                
                # 최종 신뢰도 기준으로 정렬
                final_questions.sort(key=lambda x: x.get("final_confidence", 0), reverse=True)
                
                result = {
                    "questions": final_questions,  # 검증된 문제들
                    "stats": {
                        "total_generated": len(questions),
                        "rag_filtered": len(rag_filtered_questions),
                        "final_verified": len(final_questions)
                    }
                }
                print(f"[DEBUG] 최종 검증 결과: {json.dumps(result, ensure_ascii=False, indent=2)}")
                return result
                
            except Exception as e:
                print(f"[ERROR] Critic 결과 처리 중 오류: {str(e)}")
                raise
        
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
        raise HTTPException(
            status_code=500,
            detail=f"문제 검증 중 오류가 발생했습니다: {str(e)}"
        )

def get_text_by_document_id(document_id: str, db: Session) -> str:
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).order_by(DocumentChunk.id).all()
    return " ".join(c.chunk_text for c in chunks)

@app.post("/api/generate-questions-from-document")
async def generate_questions_from_document(data: Dict, db: Session = Depends(get_vector_db), user_db: Session = Depends(get_db)):
    document_id = data.get("document_id")
    user_id = data.get("user_id", "testuser")

    # 1. 텍스트 불러오기
    text = get_text_by_document_id(document_id, db)
    if not text:
        raise HTTPException(status_code=404, detail="문서 내용 없음")
    print("[DEBUG] 문서 텍스트 불러오기 완료")

    # 2. 문제 생성
    questions = await question_generator.execute_function("generate_questions", {"text": text})
    print(f"[DEBUG] 문제 생성 완료: {len(questions)}개 생성됨")

    # 3. 유사 문제 필터링
    print("\n=== 유사 문제 필터링 시작 ===")
    existing_questions = user_db.query(Question).filter(Question.user_id == user_id).all()
    existing_q_texts = [q.question for q in existing_questions]

    print(f"\n[DEBUG] 기존 문제 수: {len(existing_questions)}")
    print("[DEBUG] 기존 문제 목록:")
    for i, q in enumerate(existing_q_texts, 1):
        print(f"{i}. {q[:100]}...")

    model = SentenceTransformer('jhgan/ko-sroberta-multitask')
    filtered_questions = []
    print("\n[DEBUG] 유사도 검사 시작")

    for i, q in enumerate(questions, 1):
        is_similar = False
        q_emb = model.encode(q["question"], convert_to_tensor=True)

        print(f"\n[DEBUG] 문제 {i} 유사도 검사:")
        print(f"검사 중인 문제: {q['question'][:100]}...")

        for j, exist_q in enumerate(existing_q_texts, 1):
            exist_emb = model.encode(exist_q, convert_to_tensor=True)
            sim = float(torch.cosine_similarity(q_emb.unsqueeze(0), exist_emb.unsqueeze(0)))
            print(f"- 기존 문제 {j}와의 유사도: {sim:.4f}")

            if sim > 0.85:
                is_similar = True
                print(f"[!] 유사 문제 발견 (유사도: {sim:.4f})")
                break

        if not is_similar:
            filtered_questions.append(q)
            print("=> 문제 추가됨 (유사하지 않음)")
        else:
            print("=> 문제 제외됨 (유사도 높음)")

    print(f"\n[DEBUG] 최종 필터링 결과:")
    print(f"- 초기 문제 수: {len(questions)}")
    print(f"- 필터링 후 문제 수: {len(filtered_questions)}")
    print(f"- 제외된 문제 수: {len(questions) - len(filtered_questions)}")
    print("\n=== 유사 문제 필터링 완료 ===\n")

    # 4. RAG 및 Critic 기반 문제 검증
    verification_result = await verify_questions_with_rag_and_critic(filtered_questions, text)
    print(f"[DEBUG] 검증 결과: {json.dumps(verification_result, ensure_ascii=False, indent=2)}")

    # 5. 응답 구조화
    response = {
        "success": True,
        "questions": verification_result.get("questions", []),
        "text": text,
        "stats": verification_result.get("stats", {
            "total_generated": len(questions),
            "filtered_for_duplicates": len(filtered_questions),
            "rag_filtered": 0,
            "final_verified": 0
        })
    }

    print(f"[DEBUG] 최종 응답: {json.dumps(response, ensure_ascii=False, indent=2)}")
    return response

@app.post("/api/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    db: Session = Depends(get_vector_db)
):
    try:
        # 1. 텍스트 추출
        text = await question_generator.execute_function("extract_text", {"file": file})
        chunks = create_overlapping_chunks(text)

        # 2. 문서 및 chunk 저장
        document_id = str(uuid4())
        filename_wo_ext = os.path.splitext(file.filename)[0]

        db.add(Document(id=document_id, user_id=user_id, filename=filename_wo_ext))

        for chunk in chunks:
            emb = rag_model.encode(chunk).tolist()
            db.add(DocumentChunk(
                user_id=user_id,
                document_id=document_id,
                chunk_text=chunk,
                embedding=emb
            ))

        db.commit()

        return {
            "success": True,
            "document_id": document_id,
            "chunk_count": len(chunks)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail="업로드 실패: " + str(e))

@app.get("/api/documents/{user_id}")
def list_documents(user_id: str, db: Session = Depends(get_vector_db)):
    docs = db.query(Document).filter(Document.user_id == user_id).order_by(Document.created_at.desc()).all()
    return [
        {"document_id": d.id, "filename": d.filename, "created_at": d.created_at.strftime("%Y-%m-%d %H:%M:%S")}
        for d in docs
    ]

@app.delete("/api/documents/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_vector_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(doc)
    db.commit()
    return {"message": "Document deleted"}

@app.post("/api/check-answers")
async def check_answers(data: Dict): # 함수 이름은 check_answers로 유지 (또는 원하는 이름)
    """여러 답안을 한 번에 평가하고, QuizSection.tsx가 기대하는 형식으로 결과를 반환합니다."""
    try:
        answers_to_evaluate = data.get("answers")
        if not isinstance(answers_to_evaluate, list):
            raise HTTPException(status_code=400, detail="answers 필드는 리스트 형태여야 합니다.")

        print(f"[DEBUG] (/api/check-answers) 답안 평가 시작: {len(answers_to_evaluate)}개 답안")

        raw_eval_result = await evaluator.execute_function(
            "evaluate_answers",
            {"answers": answers_to_evaluate}
        )

        parsed_eval_result: Dict
        if isinstance(raw_eval_result, str):
            parsed_eval_result = safe_json_loads(raw_eval_result)
        elif isinstance(raw_eval_result, dict):
            parsed_eval_result = raw_eval_result
        else:
            print(f"[ERROR] (/api/check-answers) EvaluatorAgent가 예상치 못한 타입 반환: {type(raw_eval_result)}")
            raise HTTPException(status_code=500, detail="평가 서비스로부터 잘못된 형식의 응답을 받았습니다.")

        if not isinstance(parsed_eval_result, dict):
            raise ValueError("파싱된 평가 결과가 올바른 형식이 아닙니다 (dict여야 함).")

        individual_results = parsed_eval_result.get("results", [])
        if not isinstance(individual_results, list):
            print(f"[WARNING] (/api/check-answers) 평가 결과의 'results' 필드가 리스트가 아님: {type(individual_results)}. 빈 리스트로 처리.")
            individual_results = []

        total_questions = len(individual_results)
        correct_count = 0
        for res_item in individual_results:
            if isinstance(res_item, dict) and res_item.get("is_correct") is True:
                correct_count += 1

        score_percentage = (correct_count / total_questions * 100) if total_questions > 0 else 0.0

        agent_summary = parsed_eval_result.get("summary", {})
        if not isinstance(agent_summary, dict):
            agent_summary = {}
        overall_feedback = agent_summary.get("overall_feedback", "채점이 완료되었습니다! 결과를 확인해보세요.")

        response_total_object = {
            "total_score": correct_count,
            "total_questions": total_questions,
            "score_percentage": round(score_percentage, 1),
            "overall_feedback": overall_feedback
        }

        final_response = {
            "total": response_total_object,
            "results": individual_results
        }

        print(f"[DEBUG] (/api/check-answers) 최종 API 응답: {json.dumps(final_response, ensure_ascii=False, indent=2)}")
        return final_response

    except HTTPException as he:
        raise he
    except ValueError as ve:
        print(f"[ERROR] (/api/check-answers) 답안 평가 값/형식 오류: {str(ve)}")
        raise HTTPException(status_code=500, detail=f"평가 결과 처리 중 데이터 오류 발생: {str(ve)}")
    except Exception as e:
        print(f"[ERROR] (/api/check-answers) 답안 평가 중 예기치 않은 오류: {type(e).__name__} - {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"답안 평가 중 서버 내부 오류가 발생했습니다: {str(e)}"
        )

@app.post("/api/check-answer")
async def check_answer(data: Dict):
    """단일 답안을 평가하는 엔드포인트"""
    try:
        # 데이터 유효성 검사
        required_fields = ["question", "user_answer", "correct_answer"]
        for field in required_fields:
            if field not in data:
                raise HTTPException(
                    status_code=400,
                    detail=f"필수 필드가 누락되었습니다: {field}"
                )
        
        # EvaluatorAgent를 통한 단일 답안 평가
        result = await evaluator.execute_function(
            "evaluate_single_answer",
            {"answer": data}
        )
        
        try:
            # 결과가 문자열인 경우 JSON으로 파싱
            if isinstance(result, str):
                result = safe_json_loads(result)
                
            # 응답 형식 검증 및 표준화
            if not isinstance(result, dict):
                raise ValueError("평가 결과가 올바른 형식이 아닙니다.")
                
            return {
                "success": True,
                "evaluation": {
                    "is_correct": result.get("is_correct", False),
                    "score": result.get("score", 0.0),
                    "feedback": result.get("feedback", "평가를 완료하지 못했습니다."),
                    "details": result.get("details", {})
                }
            }
            
        except Exception as e:
            print(f"평가 결과 처리 중 오류: {str(e)}")
            return {
                "success": False,
                "error": "평가 결과 처리 중 오류가 발생했습니다.",
                "details": str(e)
            }
            
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"답안 평가 중 오류: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="답안 평가 중 오류가 발생했습니다."
        )

def safe_json_loads(text: str) -> Dict:
    """안전한 JSON 파싱을 위한 유틸리티 함수"""
    try:
        # 코드 블록이나 마크다운 형식 제거
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        text = re.sub(r'`.*?`', '', text)
        
        # JSON 시작과 끝 위치 찾기
        start = text.find('{')
        end = text.rfind('}') + 1
        
        if start != -1 and end > start:
            json_str = text[start:end]
            return json.loads(json_str)
        raise ValueError("유효한 JSON을 찾을 수 없습니다.")
    except Exception as e:
        print(f"JSON 파싱 오류: {str(e)}\n원본 텍스트: {text}")
        raise

class QuestionItem(BaseModel):
    question: str
    correct_answer: str
    explanation: str
    options: List[str] = []
    type: str
    document_name: str

class SaveQuestionsRequest(BaseModel):
    user_id: str
    questions: List[QuestionItem]

@app.post("/api/save-questions")
async def save_questions(data: SaveQuestionsRequest, db: Session = Depends(get_db)):
    try:
        for q in data.questions:
            db_question = Question(
                user_id=data.user_id,
                question=q.question,
                correct_answer=q.correct_answer,
                explanation=q.explanation,
                options=q.options,
                type=q.type,
                document_name = q.document_name
            )
            db.add(db_question)
        db.commit()
        return {"success": True, "message": "문제 저장 완료"}
    except Exception as e:
        print(f"[ERROR] 문제 저장 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="문제 저장 중 오류가 발생했습니다.")

@app.get("/api/get-questions/{user_id}")
async def get_questions(user_id: str, db: Session = Depends(get_db)):
    questions = (
        db.query(Question)
        .filter(Question.user_id == user_id)
        .order_by(Question.created_at.desc())  # 최신순 정렬
        .all()
    )

    grouped = defaultdict(list)

    for q in questions:
        key = q.document_name or "미지정 문서"  # document_name이 없을 경우 대비
        grouped[key].append({
            "id": q.id,
            "question": q.question,
            "options": q.options if q.options else [],
            "correct_answer": q.correct_answer,
            "explanation": q.explanation,
            "type": q.type,
        })

    return {"grouped_questions": grouped}

@app.post("/api/generate-questions")
async def generate_questions_from_context(data: Dict, db: Session = Depends(get_db)):
    text = data["text"]
    user_id = data.get("user_id", "testuser")
    # 1. 기존 문제 불러오기
    existing_questions = db.query(Question).filter(Question.user_id == user_id, Question.question == text).all()
    existing_q_texts = [q.question for q in existing_questions]

    # 2. 새 문제 생성
    questions = await question_generator.execute_function("generate_questions", {"text": text})

    # 3. 유사/동일 문제 필터링
    model = SentenceTransformer('jhgan/ko-sroberta-multitask')
    filtered_questions = []
    for q in questions:
        is_similar = False
        q_emb = model.encode(q["question"], convert_to_tensor=True)
        for exist_q in existing_q_texts:
            exist_emb = model.encode(exist_q, convert_to_tensor=True)
            sim = float(torch.cosine_similarity(q_emb.unsqueeze(0), exist_emb.unsqueeze(0)))
            if sim > 0.85:
                is_similar = True
                break
        if not is_similar:
            filtered_questions.append(q)

    return {"questions": filtered_questions, "text": text}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 