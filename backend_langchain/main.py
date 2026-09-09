import uuid
import tempfile
from fastapi import FastAPI, UploadFile, HTTPException
from vectorstore import ingest_pdf, get_full_document_text
from graph import run_quiz_pipeline
from chains.evaluator import evaluate_answers

app = FastAPI(title="EduQuest (LangChain ver.)")


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile):
    document_id = str(uuid.uuid4())
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    chunks = ingest_pdf(tmp_path, document_id=document_id, filename=file.filename)
    return {
        "document_id": document_id,
        "filename": file.filename,
        "chunk_count": len(chunks),
    }


@app.post("/api/documents/{document_id}/generate-quiz")
async def generate_quiz(document_id: str):
    document_text = get_full_document_text(document_id)
    if not document_text:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
    final_questions = await run_quiz_pipeline(document_text, document_id)
    if not final_questions:
        raise HTTPException(status_code=422, detail="유효한 문제를 생성하지 못했습니다")
    return {
        "document_id": document_id,
        "questions": [
            {
                "question": item["question"].question,
                "options": item["question"].options,
                "correct_answer": item["question"].correct_answer,
                "explanation": item["question"].explanation,
                "grounding_similarity": item["similarity"],
            }
            for item in final_questions
        ],
    }


@app.post("/api/answers/evaluate")
async def evaluate_answers_endpoint(answers: list[dict]):
    result = await evaluate_answers(answers)
    return result.model_dump()
