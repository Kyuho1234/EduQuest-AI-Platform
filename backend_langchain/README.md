

기존 `backend/`(직접 구현한 멀티 에이전트 파이프라인)를 LangChain / LangGraph 기반으로 재구현
이중 모델 교차 검증 → 답안 채점 로직을 최대한 그대로 유지하면서, 컴포넌트를 LangChain으로 교체했습니다.

## 파일 구조

```
backend_langchain/
├── config.py               # LLM/임베딩 클라이언트 설정 (기존: 각 에이전트가 개별적으로 클라이언트 생성)
├── schemas.py               # Pydantic 구조화 출력 스키마 (기존: 정규식으로 JSON 정제)
├── vectorstore.py           # PDF 로드/청킹/임베딩/pgvector 저장 (기존: PyPDF2 + 직접 청커 + SQLAlchemy)
├── graph.py                 # LangGraph 파이프라인 오케스트레이션 (기존: main.py에 하드코딩된 순차 호출)
├── main.py                  # FastAPI 엔드포인트 예시
└── chains/
    ├── question_generator.py  # 기존 agents/question_generator.py 대체
    ├── critic.py               # 기존 agents/critic.py 대체
    └── evaluator.py            # 기존 agents/evaluator.py 대체
```

## 기존 코드 → 신규 코드 매핑

| 기존 (`backend/`) | 신규 (`backend_langchain/`) |
|---|---|
| `create_overlapping_chunks()` (직접 구현) | `RecursiveCharacterTextSplitter` |
| `SentenceTransformer` 직접 호출 | `HuggingFaceEmbeddings` |
| SQLAlchemy + pgvector 컬럼 직접 관리 | `PGVector` (langchain-postgres) |
| `google.generativeai` SDK 직접 호출 | `ChatGoogleGenerativeAI` |
| OpenRouter `requests.post()` 직접 호출 | `ChatOpenAI(base_url=...)` |
| `_clean_json_response()` 정규식 파싱 | `with_structured_output(PydanticModel)` |
| `BaseAgent.process_message()` / A2A 메시지 | `LangGraph` `StateGraph` |
| `main.py`에 하드코딩된 순차 흐름 | `graph.py`의 조건부 엣지 (실패 시 자동 재시도 포함) |

## 개선점

1. 자동 재시도: 기존은 Critic 검증에 실패하면 그냥 실패를 반환했지만(오류 발생 메시지 포함),
   `graph.py`의 `route_after_critic()`이 검증 실패 시 자동으로 재생성을 시도.
2. 구조화 출력: `with_structured_output()`이 JSON 스키마 검증과 재시도를 대신 처리해서,
   기존의 정규식 기반 JSON 정제 코드(`_clean_json_response`)가 필요 없어졌습니다.
3. 병렬 검증: 기존은 DeepSeek → Qwen을 순차 호출했지만, `RunnableParallel`로 동시에 호출해
   Critic 단계의 지연시간을 절반 가까이 줄입니다.

## 남아있는 한계 (기존과 동일하게 유지된 부분)

-  문제 생성 시 여전히 문서 전체를 컨텍스트로 사용 - (`vectorstore.get_full_document_text()`).
  top-k 검색 기반 생성으로 바꾸려면 `vectorstore.get_retriever()`를 사용하여 대체.

## 의존성 설치

```bash
pip install -r requirements.txt
```

`.env` 파일에 다음 값 필요:
```
GEMINI_API_KEY=...
OPENROUTER_API_KEY=...
VECTOR_DATABASE_URL=postgresql+psycopg://user:pass@host:port/dbname
```

기존 `DocumentChunk` 테이블의 데이터를 이 구조로 옮기려면 별도 마이그레이션 스크립트가 필요
