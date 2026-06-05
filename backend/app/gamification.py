from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, Task


ACHIEVEMENTS = {
    "first_task": {"name": "Pervyj shag", "description": "Sozdat pervuyu zadachu", "xp": 10, "emoji": "🎯"},
    "task_master": {"name": "Master zadach", "description": "Vypolnit 10 zadach", "xp": 50, "emoji": "🏆"},
    "speed_demon": {"name": "Skorostnoj", "description": "Vypolnit zadachu za den", "xp": 30, "emoji": "⚡"},
    "deadline_hero": {"name": "Geroj dedlajna", "description": "Vypolnit 5 zadach do dedlajna", "xp": 40, "emoji": "⏰"},
    "meeting_attendee": {"name": "Uchastnik vstrech", "description": "Prisutstvovat na 5 vstrechah", "xp": 25, "emoji": "🎤"},
    "report_streak_3": {"name": "Strik 3", "description": "3 dnya podryad otchety", "xp": 20, "emoji": "🔥"},
    "report_streak_7": {"name": "Strik 7", "description": "Nedelya otchetnosti", "xp": 50, "emoji": "🔥🔥"},
    "report_streak_30": {"name": "Strik 30", "description": "Mesyac otchetnosti", "xp": 150, "emoji": "🔥🔥🔥"},
    "team_player": {"name": "Komandnyj igrok", "description": "Pomoch kolegam 3 raza", "xp": 35, "emoji": "🤝"},
    "night_owl": {"name": "Nochnaya sova", "description": "Rabotat posle 22:00", "xp": 15, "emoji": "🦉"},
    "early_bird": {"name": "Rannyaya ptica", "description": "Nachat rabotu do 8:00", "xp": 15, "emoji": "🐦"},
    "kanban_master": {"name": "Master kanbana", "description": "Peremestit 20 zadach", "xp": 30, "emoji": "📊"},
}

LEVELS = [
    (0, "Novichok", "🌱"),
    (100, "Stazhyor", "🌿"),
    (300, "Specialist", "🌳"),
    (600, "Professional", "⭐"),
    (1000, "Expert", "🌟"),
    (1500, "Master", "💎"),
    (2200, "Grandmaster", "👑"),
    (3000, "Legenda", "🏆"),
]


class GamificationService:
    def __init__(self):
        self.achievements = ACHIEVEMENTS
        self.levels = LEVELS

    def get_level_info(self, xp: int) -> Dict:
        current_level = LEVELS[0]
        next_level = LEVELS[1] if len(LEVELS) > 1 else None

        for i, (threshold, name, emoji) in enumerate(LEVELS):
            if xp >= threshold:
                current_level = (threshold, name, emoji)
                next_level = LEVELS[i + 1] if i + 1 < len(LEVELS) else None

        xp_for_current = current_level[0]
        xp_for_next = next_level[0] if next_level else xp_for_current + 1000
        progress = min(1.0, (xp - xp_for_current) / max(1, xp_for_next - xp_for_current))

        return {
            "level": current_level[1],
            "level_emoji": current_level[2],
            "level_num": LEVELS.index(current_level) + 1,
            "xp": xp,
            "xp_for_next": xp_for_next,
            "progress": progress,
            "next_level_name": next_level[1] if next_level else "Maksimum"
        }

    async def add_xp(self, session: AsyncSession, user_id: str, amount: int, reason: str = "") -> Dict:
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return {"error": "User not found"}

        old_level = self.get_level_info(user.xp)
        user.xp += amount
        new_level = self.get_level_info(user.xp)

        level_up = new_level["level_num"] > old_level["level_num"]

        await session.commit()

        return {
            "xp_added": amount,
            "total_xp": user.xp,
            "new_level": new_level,
            "level_up": level_up,
            "reason": reason
        }

    async def check_achievement(self, session: AsyncSession, user_id: str, 
                                 achievement_key: str) -> Optional[Dict]:
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return None

        if achievement_key in (user.achievements or []):
            return None  # Already has it

        achievement = self.achievements.get(achievement_key)
        if not achievement:
            return None

        # Add achievement
        achievements = user.achievements or []
        achievements.append(achievement_key)
        user.achievements = achievements

        # Add XP
        xp_result = await self.add_xp(session, user_id, achievement["xp"], 
                                       f"Dostizhenie: {achievement['name']}")

        await session.commit()

        return {
            "achievement": achievement,
            "xp_result": xp_result
        }

    async def on_task_created(self, session: AsyncSession, user_id: str) -> List[Dict]:
        results = []

        # Check first task
        stmt = select(Task).where(Task.creator_id == user_id)
        result = await session.execute(stmt)
        tasks = result.scalars().all()

        if len(tasks) == 1:
            ach = await self.check_achievement(session, user_id, "first_task")
            if ach:
                results.append(ach)

        if len(tasks) >= 10:
            ach = await self.check_achievement(session, user_id, "task_master")
            if ach:
                results.append(ach)

        return results

    async def on_task_completed(self, session: AsyncSession, user_id: str, 
                                 completion_time_hours: float = None) -> List[Dict]:
        results = []

        # Add base XP
        xp_result = await self.add_xp(session, user_id, 10, "Zadacha vypolnena")
        results.append({"type": "xp", "data": xp_result})

        # Check speed demon
        if completion_time_hours and completion_time_hours <= 24:
            ach = await self.check_achievement(session, user_id, "speed_demon")
            if ach:
                results.append({"type": "achievement", "data": ach})

        # Check deadline hero
        stmt = select(Task).where(
            Task.assignee_id == user_id,
            Task.status == "done"
        )
        result = await session.execute(stmt)
        completed = result.scalars().all()

        if len(completed) >= 5:
            ach = await self.check_achievement(session, user_id, "deadline_hero")
            if ach:
                results.append({"type": "achievement", "data": ach})

        # Check kanban master
        if len(completed) >= 20:
            ach = await self.check_achievement(session, user_id, "kanban_master")
            if ach:
                results.append({"type": "achievement", "data": ach})

        return results

    async def on_daily_report(self, session: AsyncSession, user_id: str, 
                               streak_days: int) -> List[Dict]:
        results = []

        # Add XP for report
        xp_result = await self.add_xp(session, user_id, 5, "Ezhednevnyj otchyot")
        results.append({"type": "xp", "data": xp_result})

        # Check streak achievements
        streak_achievements = {
            3: "report_streak_3",
            7: "report_streak_7", 
            30: "report_streak_30"
        }

        for threshold, ach_key in streak_achievements.items():
            if streak_days >= threshold:
                ach = await self.check_achievement(session, user_id, ach_key)
                if ach:
                    results.append({"type": "achievement", "data": ach})

        return results

    async def on_meeting_attended(self, session: AsyncSession, user_id: str) -> List[Dict]:
        results = []

        xp_result = await self.add_xp(session, user_id, 5, "Uchastie vo vstrechi")
        results.append({"type": "xp", "data": xp_result})

        # Check meeting attendee
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user and user.meetings_attended >= 5:
            ach = await self.check_achievement(session, user_id, "meeting_attendee")
            if ach:
                results.append({"type": "achievement", "data": ach})

        return results

    async def get_user_profile(self, session: AsyncSession, user_id: str) -> Dict:
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return {"error": "User not found"}

        level_info = self.get_level_info(user.xp)

        user_achievements = []
        for ach_key in (user.achievements or []):
            if ach_key in self.achievements:
                ach = self.achievements[ach_key].copy()
                ach["key"] = ach_key
                user_achievements.append(ach)

        return {
            "user_id": user_id,
            "name": f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username or "User",
            "username": user.username,
            "level_info": level_info,
            "stats": {
                "tasks_completed": user.tasks_completed,
                "tasks_created": user.tasks_created,
                "meetings_attended": user.meetings_attended,
                "avg_completion_time": user.avg_completion_time
            },
            "achievements": user_achievements,
            "achievements_count": len(user_achievements),
            "total_achievements": len(self.achievements)
        }

    def get_leaderboard_text(self, users_data: List[Dict]) -> str:
        text = "🏆 *Tablitsa liderov*\n\n"

        sorted_users = sorted(users_data, key=lambda x: x.get("xp", 0), reverse=True)

        medals = ["🥇", "🥈", "🥉"]
        for i, user in enumerate(sorted_users[:10]):
            medal = medals[i] if i < 3 else f"{i+1}."
            level = user.get("level_info", {})
            text += f"{medal} {user.get('name', 'User')} | {level.get('level_emoji', '')} {level.get('level', 'N/A')} | XP: {user.get('xp', 0)}\n"

        return text


gamification_service = GamificationService()
