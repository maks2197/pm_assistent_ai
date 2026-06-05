from typing import List, Dict, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import KnowledgeEntry, Task, Meeting
from app.nlp_engine import nlp_engine
from app.config import get_settings
import json

settings = get_settings()


class KnowledgeBaseService:
    def __init__(self):
        pass

    async def add_from_meeting(self, session: AsyncSession, meeting_id: str, 
                                chat_id: str, summary: Dict) -> List[Dict]:
        entries = []

        # Add decisions
        for decision in summary.get("decisions", []):
            entry = KnowledgeEntry(
                chat_id=chat_id,
                title=f"Reshenie: {decision[:100]}",
                content=decision,
                source="meeting_summary",
                source_id=meeting_id,
                tags=["decision", "meeting"]
            )
            session.add(entry)
            entries.append({"type": "decision", "content": decision})

        # Add key points
        for point in summary.get("key_points", []):
            entry = KnowledgeEntry(
                chat_id=chat_id,
                title=f"Klyuchevoj moment: {point[:100]}",
                content=point,
                source="meeting_summary",
                source_id=meeting_id,
                tags=["key_point", "meeting"]
            )
            session.add(entry)
            entries.append({"type": "key_point", "content": point})

        # Add risks
        for risk in summary.get("risks", []):
            entry = KnowledgeEntry(
                chat_id=chat_id,
                title=f"Risk: {risk[:100]}",
                content=risk,
                source="meeting_summary",
                source_id=meeting_id,
                tags=["risk", "meeting"]
            )
            session.add(entry)
            entries.append({"type": "risk", "content": risk})

        await session.commit()
        return entries

    async def add_from_chat(self, session: AsyncSession, chat_id: str, 
                            message_text: str, message_id: str) -> Optional[Dict]:
        # Check if message contains important info (decisions, agreements, etc.)
        important_keywords = [
            "resheno", "dogovorilis'", "prinyato reshenie", "soglasovano",
            "vazhno", "ne zabyt'", "na budushchee", "arhiv", "baza znanij"
        ]

        text_lower = message_text.lower()
        is_important = any(kw in text_lower for kw in important_keywords)

        if not is_important:
            return None

        entry = KnowledgeEntry(
            chat_id=chat_id,
            title=f"Iz chata: {message_text[:100]}",
            content=message_text,
            source="chat_decision",
            source_id=message_id,
            tags=["chat", "decision"]
        )
        session.add(entry)
        await session.commit()

        return {"type": "chat_decision", "content": message_text[:200]}

    async def search(self, session: AsyncSession, chat_id: str, 
                     query: str, limit: int = 10) -> List[Dict]:
        stmt = select(KnowledgeEntry).where(
            and_(
                KnowledgeEntry.chat_id == chat_id,
                KnowledgeEntry.content.ilike(f"%{query}%")
            )
        ).order_by(KnowledgeEntry.created_at.desc()).limit(limit)

        result = await session.execute(stmt)
        entries = result.scalars().all()

        return [
            {
                "id": e.id,
                "title": e.title,
                "content": e.content,
                "source": e.source,
                "tags": e.tags,
                "created_at": e.created_at.isoformat() if e.created_at else None
            }
            for e in entries
        ]

    async def get_recent(self, session: AsyncSession, chat_id: str, 
                         limit: int = 5) -> List[Dict]:
        stmt = select(KnowledgeEntry).where(
            KnowledgeEntry.chat_id == chat_id
        ).order_by(KnowledgeEntry.created_at.desc()).limit(limit)

        result = await session.execute(stmt)
        entries = result.scalars().all()

        return [
            {
                "id": e.id,
                "title": e.title,
                "content": e.content[:300] + "..." if len(e.content) > 300 else e.content,
                "source": e.source,
                "tags": e.tags,
                "created_at": e.created_at.isoformat() if e.created_at else None
            }
            for e in entries
        ]

    async def get_by_tag(self, session: AsyncSession, chat_id: str, 
                         tag: str, limit: int = 10) -> List[Dict]:
        stmt = select(KnowledgeEntry).where(
            and_(
                KnowledgeEntry.chat_id == chat_id,
                KnowledgeEntry.tags.contains([tag])
            )
        ).order_by(KnowledgeEntry.created_at.desc()).limit(limit)

        result = await session.execute(stmt)
        entries = result.scalars().all()

        return [
            {
                "id": e.id,
                "title": e.title,
                "content": e.content[:300] + "..." if len(e.content) > 300 else e.content,
                "tags": e.tags,
                "created_at": e.created_at.isoformat() if e.created_at else None
            }
            for e in entries
        ]

    async def generate_team_wiki(self, session: AsyncSession, chat_id: str) -> str:
        stmt = select(KnowledgeEntry).where(
            KnowledgeEntry.chat_id == chat_id
        ).order_by(KnowledgeEntry.created_at.desc())

        result = await session.execute(stmt)
        entries = result.scalars().all()

        wiki = "📚 *Baza znanij komandy*\n\n"

        # Group by source
        by_source = {}
        for e in entries:
            src = e.source or "other"
            if src not in by_source:
                by_source[src] = []
            by_source[src].append(e)

        for source, items in by_source.items():
            emoji = {"meeting_summary": "🎤", "chat_decision": "💬", "manual": "📝"}.get(source, "📄")
            wiki += f"\n{emoji} *{source.replace('_', ' ').title()}*\n"
            for item in items[:5]:
                wiki += f"- {item.title}\n"

        return wiki


knowledge_base_service = KnowledgeBaseService()
