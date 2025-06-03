# services/vector_service.py
import json
from sentence_transformers import SentenceTransformer
from db.db1 import SessionDB1
from models.vector_doc import VectorDocument

model = SentenceTransformer('jhgan/ko-sroberta-multitask')

async def save_text_vector(text: str):
    embedding = model.encode(text).tolist()

    async with SessionDB1() as session:
        doc = VectorDocument(
            content=text,
            embedding=json.dumps(embedding)
        )
        session.add(doc)
        await session.commit()
