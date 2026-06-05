from sqlalchemy import Column, String, DateTime, Integer, Boolean, JSON, ForeignKey, Text, Float
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import uuid

Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    telegram_id = Column(String, unique=True, index=True)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    role = Column(String, default="member")  # admin, member, viewer
    created_at = Column(DateTime, default=datetime.utcnow)

    # Gamification
    xp = Column(Integer, default=0)
    level = Column(Integer, default=1)
    achievements = Column(JSON, default=list)
    streak_days = Column(Integer, default=0)

    # Stats
    tasks_completed = Column(Integer, default=0)
    tasks_created = Column(Integer, default=0)
    meetings_attended = Column(Integer, default=0)
    avg_completion_time = Column(Float, default=0.0)


class Chat(Base):
    __tablename__ = "chats"

    id = Column(String, primary_key=True, default=generate_uuid)
    telegram_chat_id = Column(String, unique=True, index=True)
    title = Column(String)
    type = Column(String)  # group, supergroup, channel
    yougile_board_id = Column(String)
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=generate_uuid)
    yougile_task_id = Column(String, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, default="backlog")  # backlog, todo, in_progress, review, done
    priority = Column(String, default="medium")  # low, medium, high, critical

    assignee_id = Column(String, ForeignKey("users.id"))
    creator_id = Column(String, ForeignKey("users.id"))
    chat_id = Column(String, ForeignKey("chats.id"))

    deadline = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)

    source = Column(String)  # telegram_chat, meeting, manual
    source_message_id = Column(String)

    # NLP extracted data
    extracted_deadline = Column(DateTime)
    extracted_assignees = Column(JSON, default=list)
    confidence_score = Column(Float, default=0.0)

    # Reminders
    reminder_sent = Column(Boolean, default=False)
    overdue_notified = Column(Boolean, default=False)


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String)
    platform = Column(String)  # yandex_telemost, zoom, teams, simulated
    meeting_url = Column(String)
    scheduled_at = Column(DateTime)
    duration_minutes = Column(Integer)

    chat_id = Column(String, ForeignKey("chats.id"))
    organizer_id = Column(String, ForeignKey("users.id"))

    status = Column(String, default="scheduled")  # scheduled, active, completed, cancelled

    # Audio/Transcript
    transcript = Column(Text)
    summary = Column(Text)
    action_items = Column(JSON, default=list)
    audio_file_path = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)


class DailyReport(Base):
    __tablename__ = "daily_reports"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"))
    chat_id = Column(String, ForeignKey("chats.id"))
    date = Column(DateTime)
    report_text = Column(Text)

    # Parsed tasks from report
    tasks_mentioned = Column(JSON, default=list)
    tasks_completed = Column(JSON, default=list)
    tasks_in_progress = Column(JSON, default=list)
    tasks_blocked = Column(JSON, default=list)

    status = Column(String, default="pending")  # pending, verified, flagged
    created_at = Column(DateTime, default=datetime.utcnow)


class KnowledgeEntry(Base):
    __tablename__ = "knowledge_base"

    id = Column(String, primary_key=True, default=generate_uuid)
    chat_id = Column(String, ForeignKey("chats.id"))
    title = Column(String)
    content = Column(Text)
    source = Column(String)  # meeting_summary, chat_decision, manual
    source_id = Column(String)  # meeting_id or message_id
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(String, primary_key=True, default=generate_uuid)
    task_id = Column(String, ForeignKey("tasks.id"))
    user_id = Column(String, ForeignKey("users.id"))
    chat_id = Column(String, ForeignKey("chats.id"))

    reminder_type = Column(String)  # deadline, status_update, meeting, evening_sync
    scheduled_at = Column(DateTime)
    sent_at = Column(DateTime)
    message_text = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)


# Database setup
engine = None
async_session = None


def init_db(database_url: str):
    global engine, async_session
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, async_session


async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
