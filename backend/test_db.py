import asyncio

from app.db.database import Base, engine
from app.models.analysis import Analysis


async def test():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("Database connection: OK")
    print("Database tables: CREATED")


asyncio.run(test())
