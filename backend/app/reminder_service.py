import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Task, User, Chat, Reminder
from app.config import get_settings
from app.nlp_engine import nlp_engine

settings = get_settings()


class ReminderService:
    def __init__(self):
        self.check_interval = settings.REMINDER_CHECK_INTERVAL

    async def check_deadlines(self, session: AsyncSession, bot) -> List[Dict]:
        now = datetime.now()
        two_hours = now + timedelta(hours=2)

        # Find tasks with approaching deadlines
        stmt = select(Task).where(
            and_(
                Task.deadline <= two_hours,
                Task.deadline > now,
                Task.reminder_sent == False,
                Task.status != "done"
            )
        )
        result = await session.execute(stmt)
        tasks = result.scalars().all()

        sent_reminders = []
        for task in tasks:
            # Get assignee
            user_stmt = select(User).where(User.id == task.assignee_id)
            user_result = await session.execute(user_stmt)
            user = user_result.scalar_one_or_none()

            if user and user.telegram_id:
                message = await nlp_engine.generate_reminder_message(
                    task.title, task.deadline, user.username or user.first_name or "user"
                )

                try:
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=message,
                        parse_mode="Markdown"
                    )
                    task.reminder_sent = True
                    sent_reminders.append({"task_id": task.id, "user_id": user.id})
                except Exception as e:
                    print(f"Failed to send reminder: {e}")

        await session.commit()
        return sent_reminders

    async def check_overdue(self, session: AsyncSession, bot) -> List[Dict]:
        now = datetime.now()

        stmt = select(Task).where(
            and_(
                Task.deadline < now,
                Task.overdue_notified == False,
                Task.status != "done"
            )
        )
        result = await session.execute(stmt)
        tasks = result.scalars().all()

        notifications = []
        for task in tasks:
            user_stmt = select(User).where(User.id == task.assignee_id)
            user_result = await session.execute(user_stmt)
            user = user_result.scalar_one_or_none()

            if user and user.telegram_id:
                message = f"🚨 @{user.username or user.first_name} ZADACHA PROSROCHENA: **{task.title}**\n\nNemedlenno obnovite status ili ustanovite novyj dedlajn!"

                try:
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=message,
                        parse_mode="Markdown"
                    )
                    task.overdue_notified = True
                    notifications.append({"task_id": task.id, "type": "overdue"})
                except Exception as e:
                    print(f"Failed to send overdue notification: {e}")

        await session.commit()
        return notifications

    async def check_status_updates(self, session: AsyncSession, bot) -> List[Dict]:
        # Check tasks that haven't been updated in 48 hours
        two_days_ago = datetime.now() - timedelta(hours=48)

        stmt = select(Task).where(
            and_(
                Task.updated_at < two_days_ago,
                Task.status.in_(["todo", "in_progress"]),
                Task.reminder_sent == False
            )
        )
        result = await session.execute(stmt)
        tasks = result.scalars().all()

        notifications = []
        for task in tasks:
            user_stmt = select(User).where(User.id == task.assignee_id)
            user_result = await session.execute(user_stmt)
            user = user_result.scalar_one_or_none()

            if user and user.telegram_id:
                message = f"📊 @{user.username or user.first_name}, vy ne obnovlyali status zadachi **{task.title}** bolee 2 dnej.\n\nTekushchij status: {task.status}"

                try:
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=message,
                        parse_mode="Markdown"
                    )
                    notifications.append({"task_id": task.id, "type": "status_update"})
                except Exception as e:
                    print(f"Failed to send status reminder: {e}")

        return notifications

    async def schedule_meeting_reminder(self, session: AsyncSession, meeting_id: str, 
                                         chat_id: str, scheduled_at: datetime, bot):
        ten_minutes_before = scheduled_at - timedelta(minutes=10)

        if datetime.now() >= ten_minutes_before and datetime.now() < scheduled_at:
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"⏰ Napominanie: vstrecha nachinaetsya cherez 10 minut!"
                )
            except Exception as e:
                print(f"Failed to send meeting reminder: {e}")

    async def run_reminder_cycle(self, session: AsyncSession, bot):
        while True:
            try:
                await self.check_deadlines(session, bot)
                await self.check_overdue(session, bot)
                await self.check_status_updates(session, bot)
            except Exception as e:
                print(f"Reminder cycle error: {e}")

            await asyncio.sleep(self.check_interval)


reminder_service = ReminderService()
