from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

DB2_URL = f"postgresql+asyncpg://{os.getenv('DB2_USER')}:{os.getenv('DB2_PASSWORD')}@113.198.66.75:10229/{os.getenv('DB2_DATABASE')}"

engine_db2 = create_async_engine(DB2_URL, echo=True)
SessionDB2 = sessionmaker(engine_db2, class_=AsyncSession, expire_on_commit=False)
