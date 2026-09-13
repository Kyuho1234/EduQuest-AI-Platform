import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from langchain_huggingface import HuggingFaceEmbeddings

from models.question import Question

DB2_URL = (
    f"postgresql+asyncpg://{os.getenv('DB2_USER', 'db2_user')}:"
    f"{os.getenv('DB2_PASSWORD', 'db2_pass')}@113.198.66.75:10229/"
    f"{os.getenv('DB2_DATABASE', 'db2_database')}"
)
engine_routing = create_async_engine(DB2_URL)
SessionRouting = sessionmaker(engine_routing, class_=AsyncSession, expire_on_commit=False)

embeddings = HuggingFaceEmbeddings(model_name="jhgan/ko-sroberta-multitask")

# main.py의 중복 문제 필터링(유사도 > 0.85면 아예 제거)과 겹치지 않도록 의도적으로 낮은 값을 씁니다.
# Critic 단계에 도달하는 문제는 이미 기존 문제와의 유사도가 0.85 이하인 것들뿐이므로,
# 그 안에서 "그래도 어느 정도 비슷한 패턴(0.6 이상)"과 "완전히 새로운 유형(0.6 미만)"을 나눕니다.
LIGHT_ROUTE_THRESHOLD = 0.6


async def get_routing_decision(question_text: str) -> dict:
    query_vec = embeddings.embed_query(question_text)

    async with SessionRouting() as session:
        stmt = (
            select(Question, Question.embedding.cosine_distance(query_vec).label("distance"))
            .where(Question.embedding.isnot(None))
            .order_by("distance")
            .limit(1)
        )
        result = await session.execute(stmt)
        row = result.first()

    if row is None:
        return {"route": "heavy", "reason": "검증된 과거 문제가 아직 없음", "similarity": None}

    _, distance = row
    similarity = 1 - distance

    if similarity >= LIGHT_ROUTE_THRESHOLD:
        return {
            "route": "light",
            "reason": "기존에 검증 통과한 문제와 유사도가 높음",
            "similarity": similarity,
        }

    return {
        "route": "heavy",
        "reason": "새로운 유형이거나 기존 검증 사례와 유사도가 낮음",
        "similarity": similarity,
    }


def embed_question(text: str) -> list[float]:
    return embeddings.embed_query(text)
