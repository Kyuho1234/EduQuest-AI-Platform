# vector_documents 테이블 마이그레이션

`embedding` 컬럼을 `Text`(JSON 문자열)에서 pgvector의 `Vector(768)` 타입으로 바꾸는 작업입니다.
기존 데이터는 재계산할 필요 없이, 저장된 JSON 배열을 그대로 벡터 타입으로 옮기면 됩니다.

DB에 직접 연결해서 아래 순서로 실행하세요 (한 번만 실행하면 됩니다).

## 1. pgvector 확장 활성화 (DB1에 아직 없다면)

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## 2. 새 컬럼 추가 → 데이터 이관 → 기존 컬럼 교체

```sql
-- 1) 새 벡터 컬럼 추가
ALTER TABLE vector_documents ADD COLUMN embedding_vec vector(768);

-- 2) 기존 JSON 문자열 데이터를 벡터로 변환해서 채우기
UPDATE vector_documents
SET embedding_vec = embedding::jsonb::text::vector;

-- 3) 컬럼 교체
ALTER TABLE vector_documents DROP COLUMN embedding;
ALTER TABLE vector_documents RENAME COLUMN embedding_vec TO embedding;
ALTER TABLE vector_documents ALTER COLUMN embedding SET NOT NULL;
```

## 3. 검색 성능을 위한 인덱스 추가 (문서량이 늘어날 걸 대비해서 권장)

```sql
CREATE INDEX ON vector_documents
USING hnsw (embedding vector_cosine_ops);
```

## 확인

```sql
SELECT id, embedding IS NOT NULL AS has_vector
FROM vector_documents
LIMIT 5;
```

마이그레이션 완료 후 `services/rag_service.py`의 `find_similar_contexts()`가
`ORDER BY embedding <-> :query_vector LIMIT k` 방식(SQLAlchemy의 `.cosine_distance()`)으로
DB 레벨에서 top-k를 직접 조회하도록 이미 수정되어 있습니다.
