from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ConversationTurn


class MemoryService:
    async def add_turn(
        self,
        session: AsyncSession,
        *,
        session_id: str,
        role: str,
        content: str,
        emotion: str | None = None,
    ) -> ConversationTurn:
        turn = ConversationTurn(
            session_id=session_id,
            role=role,
            content=content,
            emotion=emotion,
        )
        session.add(turn)
        await session.commit()
        await session.refresh(turn)
        return turn

    async def get_recent_turns(
        self, session: AsyncSession, *, session_id: str, limit: int = 8
    ) -> list[ConversationTurn]:
        stmt = (
            select(ConversationTurn)
            .where(ConversationTurn.session_id == session_id)
            .order_by(ConversationTurn.created_at.desc(), ConversationTurn.id.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(reversed(result.scalars().all()))

    async def clear_session(self, session: AsyncSession, *, session_id: str) -> int:
        stmt = delete(ConversationTurn).where(ConversationTurn.session_id == session_id)
        result = await session.execute(stmt)
        await session.commit()
        return int(result.rowcount or 0)
