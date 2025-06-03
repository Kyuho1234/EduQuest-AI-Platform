# create_db.py
import asyncio
from db.db1 import engine_db1
from db.db2 import engine_db2
from models.vector_doc import Base as BaseDB1
from models.question import Base as BaseDB2

async def init_db():
    async with engine_db1.begin() as conn:
        await conn.run_sync(BaseDB1.meta.create_all)

    async with engine_db2.begin() as conn:
        await conn.run_sync(BaseDB2.meta.create_all)

if __name__ == "__main__":
    asyncio.run(init_db())
