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

1. 새 문제가 생성되면, `main.py`가 먼저 기존 문제와 유사도가 **0.85 초과**면 아예 제거합니다 (중복 방지 필터링 — 기존 로직, 변경 없음).
2. 필터링을 통과한 문제(즉 유사도가 항상 0.85 이하인 문제)만 `agents/critic.py`로 넘어갑니다.
3. `agents/critic.py`가 `services/routing_service.get_routing_decision()`을 호출해서, 그 문제가 기존 검증 통과 문제와 얼마나 비슷한지 다시 확인합니다. 이때 임계값은 **0.6**으로, 1번의 0.85보다 의도적으로 낮게 잡았습니다 — 그래야 1번을 통과한 문제들(유사도 0~0.85 사이) 안에서도 "그래도 어느 정도 비슷한 패턴(0.6~0.85)"과 "꽤 새로운 유형(0.6 미만)"을 구분할 수 있습니다.
4. 유사도가 0.6 이상이면 → **light 경로**: 모델 1개(primary)로만 검증
5. 0.6 미만이거나 비교 대상이 없으면 → **heavy 경로**: 기존처럼 모델 2개(primary+secondary)로 교차 검증
6. 검증을 통과한 문제가 `/api/save-questions`로 저장될 때 임베딩도 함께 저장되어, 다음 라우팅 판단의 비교 대상이 됨 (누적될수록 light 경로 판단의 근거가 늘어남)

> ⚠️ 두 임계값(0.85, 0.6)은 서로 다른 목적입니다. 0.85는 "너무 비슷하면 아예 버린다"(main.py), 0.6은 "그래도 어느 정도 비슷하면 검증을 가볍게 한다"(critic.py)입니다. 같은 값을 쓰면 두 로직이 충돌합니다 — 필터링을 통과한 문제는 정의상 항상 0.85 이하이므로, 0.85를 라우팅 기준으로도 쓰면 light 경로가 사실상 실행되지 않습니다.
