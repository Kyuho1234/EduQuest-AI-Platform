from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

DB1_URL = f"postgresql+asyncpg://{os.getenv('DB1_USER')}:{os.getenv('DB1_PASSWORD')}@113.198.66.75:13229/{os.getenv('DB1_DATABASE')}"

engine_db1 = create_async_engine(DB1_URL, echo=True)
SessionDB1 = sessionmaker(engine_db1, class_=AsyncSession, expire_on_commit=False)
