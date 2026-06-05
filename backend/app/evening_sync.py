import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import DailyReport, Task, User, Chat
from app.nlp_engine import nlp_engine
from app.kanban_service import get_kanban_service


class EveningSyncService:
    def __init__(self):
        self.kanban = get_kanban_service()

    async def process_daily_report(self, session: AsyncSession, user_id: str, chat_id: str, 
                                    report_text: str) -> Dict:
        kanban_tasks = await self.kanban.get_tasks()
        analysis = await nlp_engine.analyze_daily_report(report_text, kanban_tasks)

        report = DailyReport(
            user_id=user_id,
            chat_id=chat_id,
            date=datetime.now(),
            report_text=report_text,
            tasks_mentioned=analysis.get("tasks_completed", []) + analysis.get("tasks_in_progress", []),
            tasks_completed=analysis.get("tasks_completed", []),
            tasks_in_progress=analysis.get("tasks_in_progress", []),
            tasks_blocked=analysis.get("tasks_blocked", []),
            status=analysis.get("status", "pending")
        )
        session.add(report)
        await session.commit()

        for task_id in analysis.get("tasks_completed", []):
            await self.kanban.sync_task_status(task_id, "done")

        for task_id in analysis.get("tasks_in_progress", []):
            await self.kanban.sync_task_status(task_id, "in_progress")

        return {
            "report_id": report.id,
            "status": analysis.get("status"),
            "tasks_completed": len(analysis.get("tasks_completed", [])),
            "tasks_in_progress": len(analysis.get("tasks_in_progress", [])),
            "notes": analysis.get("notes", "")
        }

    async def check_missing_reports(self, session: AsyncSession, chat_id: str) -> List[Dict]:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        stmt = select(User).where(User.id.in_(
            select(Task.assignee_id).where(Task.chat_id == chat_id)
        ))
        result = await session.execute(stmt)
        users = result.scalars().all()

        report_stmt = select(DailyReport).where(
            and_(
                DailyReport.chat_id == chat_id,
                DailyReport.date >= today
            )
        )
        report_result = await session.execute(report_stmt)
        submitted_user_ids = {r.user_id for r in report_result.scalars().all()}

        missing = []
        for user in users:
            if user.id not in submitted_user_ids:
                missing.append({
                    "user_id": user.id,
                    "telegram_id": user.telegram_id,
                    "username": user.username,
                    "first_name": user.first_name
                })

        return missing

    async def send_evening_summary(self, session: AsyncSession, chat_id: str, bot) -> Dict:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        stmt = select(Task).where(
            and_(
                Task.chat_id == chat_id,
                Task.created_at >= today
            )
        )
        result = await session.execute(stmt)
        tasks = result.scalars().all()

        done_count = sum(1 for t in tasks if t.status == "done")
        in_progress = sum(1 for t in tasks if t.status == "in_progress")
        pending = sum(1 for t in tasks if t.status in ["backlog", "todo"])

        summary = "📊 *Vechernyaya svodka*\n\n"
        summary += f"*Segodnya v komande:*\n"
        summary += f"- Zaversheno zadach: {done_count}\n"
        summary += f"- V rabote: {in_progress}\n"
        summary += f"- Ozhidayut: {pending}\n\n"
        summary += "*Zadachi na zavtra:*\n"

        tomorrow = datetime.now() + timedelta(days=1)
        upcoming_stmt = select(Task).where(
            and_(
                Task.chat_id == chat_id,
                Task.deadline <= tomorrow,
                Task.status != "done"
            )
        )
        upcoming_result = await session.execute(upcoming_stmt)
        upcoming = upcoming_result.scalars().all()

        for task in upcoming[:10]:
            assignee_stmt = select(User).where(User.id == task.assignee_id)
            assignee_result = await session.execute(assignee_stmt)
            assignee = assignee_result.scalar_one_or_none()
            name = f"@{assignee.username}" if assignee and assignee.username else (assignee.first_name if assignee else "Ne naznachen")
            dl = f", do {task.deadline.strftime('%H:%M')}" if task.deadline else ""
            summary += f"\n- {task.title} ({name}{dl})"

        missing = await self.check_missing_reports(session, chat_id)
        if missing:
            summary += "\n\n⚠️ *Ne polucheny otchety ot:*\n"
            for m in missing:
                name = f"@{m['username']}" if m['username'] else m['first_name']
                summary += f"- {name}\n"

        try:
            await bot.send_message(
                chat_id=chat_id,
                text=summary,
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Failed to send evening summary: {e}")

        return {
            "tasks_total": len(tasks),
            "done": done_count,
            "in_progress": in_progress,
            "pending": pending,
            "missing_reports": len(missing)
        }

    async def send_personal_summary(self, session: AsyncSession, user_id: str, bot) -> Dict:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        stmt = select(Task).where(
            and_(
                Task.assignee_id == user_id,
                Task.created_at >= today - timedelta(days=7)
            )
        )
        result = await session.execute(stmt)
        tasks = result.scalars().all()

        user_stmt = select(User).where(User.id == user_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if not user or not user.telegram_id:
            return {"error": "User not found or no telegram_id"}

        personal = "🎯 *Vash lichnyj otchyot*\n\n"
        personal += "*Aktivnye zadachi:*\n"

        active_tasks = [t for t in tasks if t.status != "done"]
        for task in active_tasks[:5]:
            status_emoji = {"todo": "⬜", "in_progress": "🔄", "review": "👀", "backlog": "📋"}.get(task.status, "⬜")
            deadline_str = f", do {task.deadline.strftime('%d.%m %H:%M')}" if task.deadline else ""
            personal += f"\n{status_emoji} {task.title}{deadline_str}"

        if not active_tasks:
            personal += "\n_Vse zadachi vypolneny! Otlichnyj den._"

        personal += f"\n\n⭐ *Vash progress:*\nUroven: {user.level} | Opyt: {user.xp} | Strik: {user.streak_days} dnej"

        try:
            await bot.send_message(
                chat_id=user.telegram_id,
                text=personal,
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Failed to send personal summary: {e}")

        return {
            "user_id": user_id,
            "active_tasks": len(active_tasks),
            "level": user.level,
            "xp": user.xp
        }


evening_sync_service = EveningSyncService()
