from collections.abc import AsyncIterator

from sqlalchemy import delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.models import Base, ConversationTurn

settings = get_settings()


def _make_engine(database_url: str):
    return create_async_engine(
        database_url,
        future=True,
        echo=False,
        pool_pre_ping=True,
    )


engine = _make_engine(settings.database_url)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
active_database_url = settings.database_url


async def init_db() -> None:
    global engine, SessionLocal, active_database_url

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        active_database_url = settings.database_url
    except SQLAlchemyError:
        if not (
            settings.allow_sqlite_fallback
            and settings.database_url.startswith("mysql+")
        ):
            raise

        fallback_engine = _make_engine(settings.sqlite_fallback_url)
        async with fallback_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        engine = fallback_engine
        SessionLocal = async_sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )
        active_database_url = settings.sqlite_fallback_url


async def clear_all_conversation_history() -> None:
    async with SessionLocal() as session:
        await session.execute(delete(ConversationTurn))
        await session.commit()


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
