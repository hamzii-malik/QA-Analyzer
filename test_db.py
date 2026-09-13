import asyncio

from app.db.database import engine


async def test():
    async with engine.connect() as conn:
        print("PostgreSQL + SQLAlchemy connection: OK")


asyncio.run(test())
