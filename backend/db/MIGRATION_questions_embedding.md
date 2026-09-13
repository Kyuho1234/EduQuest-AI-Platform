# questions 테이블에 embedding 컬럼 추가 (동적 라우팅용)

`Critic` 검증 단계에서 벡터 유사도 기반 동적 라우팅(가벼운 경로/무거운 경로)을 적용하기 위해,
이미 검증 통과한 문제들의 임베딩을 `questions` 테이블에 저장해야 합니다.

## 1. pgvector 확장 활성화 (DB2에 아직 없다면)

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## 2. 컬럼 추가

```sql
ALTER TABLE questions ADD COLUMN embedding vector(768);
```

기존에 저장된 문제들은 embedding이 NULL인 채로 남아있어도 무방합니다.
`routing_service.get_routing_decision()`은 `embedding IS NOT NULL`인 행만 비교 대상으로 삼습니다.
(원한다면 과거 문제들도 배치 스크립트로 임베딩을 채워 넣을 수 있습니다.)

## 3. 검색 성능을 위한 인덱스 (문제 수가 많아질 걸 대비해서 권장)

```sql
CREATE INDEX ON questions USING hnsw (embedding vector_cosine_ops);
```

## 동작 방식 요약

1. 새 문제가 생성되면, `agents/critic.py`가 `services/routing_service.get_routing_decision()`을 호출
2. `questions` 테이블에서 임베딩이 있는 문제들 중 코사인 유사도가 가장 높은 것을 찾음
3. 유사도가 `LIGHT_ROUTE_THRESHOLD`(기본 0.85) 이상이면 → **light 경로**: 모델 1개(primary)로만 검증
4. 그 미만이거나 비교 대상이 없으면 → **heavy 경로**: 기존처럼 모델 2개(primary+secondary)로 교차 검증
5. 검증을 통과한 문제가 `/api/save-questions`로 저장될 때 임베딩도 함께 저장되어, 다음 라우팅 판단의 비교 대상이 됨 (누적될수록 light 경로 판단의 근거가 늘어남)
