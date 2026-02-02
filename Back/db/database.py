import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# Modules
from Back.db.models import Base

DB_URL = "sqlite+aiosqlite:///./mediScan.db" # local db for testing (TO DO: connect to postgres)

print(f"Connecting to Database: {DB_URL.split('@')[-1]}")

engine = create_async_engine(DB_URL)
get_async_session = async_sessionmaker(engine, expire_on_commit=False)

async def create_db_and_tables():
  async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)

async def get_db():
  async with get_async_session() as session:
    yield session
