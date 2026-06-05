import asyncio
import re
from datetime import datetime, timedelta
from typing import Optional
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.enums import ParseMode
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import User, Chat, Task, Meeting, get_db, init_db
from app.nlp_engine import nlp_engine
from app.kanban_service import get_kanban_service
from app.meeting_service import meeting_service
from app.reminder_service import reminder_service
from app.evening_sync import evening_sync_service
from app.gamification import gamification_service
from app.knowledge_base import knowledge_base_service

settings = get_settings()

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
router = Router()
kanban = get_kanban_service()


@router.message(Command("start"))
async def cmd_start(message: Message):
    text = (
        "Privet! Ya AI-assistent project-menedzhera.\n\n"
        "Ya avtomaticheski:\n"
        "- Sozdayu zadachi iz vashej perepiski\n"
        "- Slushayu vstrechi i vynosu zadachi\n"
        "- Napominayu o dedlajnakh\n"
        "- Vedu vechernyuyu svodku\n"
        "- Otslezhivayu progress komandy\n\n"
        "Dobav menya v gruppovoj chat, i ya nachnu rabotat!\n\n"
        "Komandy:\n"
        "/tasks - Moi zadachi\n"
        "/profile - Moj profil\n"
        "/meeting - Nachat demo-vstrechu\n"
        "/report - Otpravit ezhednevnyj otchyot\n"
        "/wiki - Baza znanij\n"
        "/leaderboard - Tablitsa liderov\n"
        "/help - Spravka"
    )
    await message.answer(text)


@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "Spravka po komandam\n\n"
        "Osnovnye:\n"
        "/start - Nachalo raboty\n"
        "/tasks - Pokazat moi zadachi\n"
        "/profile - Moj profil i dostizheniya\n\n"
        "Upravlenie zadachami:\n"
        "/task <nazvanie> - Sozdat zadachu\n"
        "/done <nazvanie> - Otmetit vypolnennoj\n"
        "/status <nazvanie> <status> - Izmenit status\n\n"
        "Vstrechi:\n"
        "/meeting - Nachat demo-vstrechu (simulyaciya)\n"
        "/summary <id> - Pokazat samari vstrechi\n\n"
        "Otchetnost:\n"
        "/report <tekst> - Otpravit ezhednevnyj otchyot\n"
        "/summary_evening - Vechernyaya svodka (admin)\n\n"
        "Baza znanij:\n"
        "/wiki - Pokazat bazu znanij\n"
        "/search <zapros> - Poisk v baze znanij\n\n"
        "Gamifikaciya:\n"
        "/leaderboard - Tablitsa liderov\n"
        "/achievements - Moi dostizheniya\n\n"
        "Admin:\n"
        "/settings - Nastrojki bota\n"
        "/remind_all - Napomnit vsem o zadachakh"
    )
    await message.answer(text)

@router.message(Command("tasks"))
async def cmd_tasks(message: Message):
    async for session in get_db():
        user_stmt = select(User).where(User.telegram_id == str(message.from_user.id))
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if not user:
            await message.answer("Vy eshche ne zaregistrirovany. Otpravte /start")
            return
        stmt = select(Task).where(and_(Task.assignee_id == user.id, Task.status != "done")).order_by(Task.deadline)
        result = await session.execute(stmt)
        tasks = result.scalars().all()
        if not tasks:
            await message.answer("U vas net aktivnykh zadach! Otlichnyj den.")
            return
        text = "Vashi zadachi:\n\n"
        for task in tasks[:10]:
            status_emoji = {"todo": "[ ]", "in_progress": "[~]", "review": "[?]", "backlog": "[-]"}.get(task.status, "[ ]")
            dl = f" (do {task.deadline.strftime('%d.%m %H:%M')})" if task.deadline else ""
            text += f"{status_emoji} {task.title}{dl}\n"
        await message.answer(text)


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    async for session in get_db():
        user_stmt = select(User).where(User.telegram_id == str(message.from_user.id))
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if not user:
            await message.answer("Vy eshche ne zaregistrirovany. Otpravte /start")
            return
        profile = await gamification_service.get_user_profile(session, user.id)
        level = profile["level_info"]
        text = (
            f"Vash profil\n\n"
            f"Imya: {profile['name']}\n"
            f"Uroven: {level['level']} ({level['level_num']})\n"
            f"Opyt: {level['xp']} / {level['xp_for_next']} XP\n"
            f"Progress: {int(level['progress'] * 100)}%\n\n"
            f"Statistika:\n"
            f"- Zadachi sozdany: {profile['stats']['tasks_created']}\n"
            f"- Zadachi vypolneny: {profile['stats']['tasks_completed']}\n"
            f"- Vstrech poseshcheno: {profile['stats']['meetings_attended']}\n\n"
            f"Dostizheniya: {profile['achievements_count']} / {profile['total_achievements']}\n"
        )
        if profile['achievements']:
            text += "\nPoluchennye:\n"
            for ach in profile['achievements'][:5]:
                text += f"- {ach['name']}\n"
        await message.answer(text)


@router.message(Command("task"))
async def cmd_create_task(message: Message):
    task_text = message.text.replace("/task", "").strip()
    if not task_text:
        await message.answer("Ispolzujte: /task <nazvanie zadachi>")
        return
    async for session in get_db():
        user_stmt = select(User).where(User.telegram_id == str(message.from_user.id))
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if not user:
            await message.answer("Vy eshche ne zaregistrirovany.")
            return
        kanban_task = await kanban.create_task(title=task_text, assignee_id=user.id)
        task = Task(
            yougile_task_id=kanban_task.get("id", ""),
            title=task_text,
            assignee_id=user.id,
            creator_id=user.id,
            source="manual",
            status="todo"
        )
        session.add(task)
        await session.commit()
        await gamification_service.on_task_created(session, user.id)
        await message.answer(f"Zadacha sozdana: {task_text}")


@router.message(Command("done"))
async def cmd_done(message: Message):
    task_title = message.text.replace("/done", "").strip()
    if not task_title:
        await message.answer("Ispolzujte: /done <nazvanie zadachi>")
        return
    async for session in get_db():
        user_stmt = select(User).where(User.telegram_id == str(message.from_user.id))
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if not user:
            await message.answer("Vy eshche ne zaregistrirovany.")
            return
        stmt = select(Task).where(and_(Task.assignee_id == user.id, Task.title.ilike(f"%{task_title}%")))
        result = await session.execute(stmt)
        task = result.scalar_one_or_none()
        if not task:
            await message.answer("Zadacha ne najdena.")
            return
        task.status = "done"
        task.completed_at = datetime.now()
        if task.yougile_task_id:
            await kanban.close_task(task.yougile_task_id)
        completion_time = None
        if task.created_at:
            completion_time = (datetime.now() - task.created_at).total_seconds() / 3600
        rewards = await gamification_service.on_task_completed(session, user.id, completion_time)
        await session.commit()
        text = f"Zadacha {task.title} vypolnena!"
        for reward in rewards:
            if reward["type"] == "achievement":
                ach = reward["data"]["achievement"]
                text += f"\n\nNovoe dostizhenie: {ach['name']}! (+{ach['xp']} XP)"
            elif reward["type"] == "xp" and reward["data"].get("level_up"):
                text += f"\n\nNovyj uroven! {reward['data']['new_level']['level']}"
        await message.answer(text)

@router.message(Command("meeting"))
async def cmd_meeting(message: Message):
    await message.answer("Zapuskayu demo-vstrechu...")
    chat_id = str(message.chat.id)
    result = await meeting_service.simulate_yandex_telemost(chat_id, bot)
    if "error" in result:
        await message.answer(f"Oshibka: {result['error']}")
        return
    summary = result.get("summary", {})
    text = "Vstrecha zavershena!\n\n"
    text += f"Samari:\n{summary.get('summary', 'Net dostupnogo rezume')}\n\n"
    text += "Klyuchevye momenty:\n"
    for point in summary.get("key_points", [])[:5]:
        text += f"- {point}\n"
    text += "\nZadachi iz vstrechi:\n"
    for item in summary.get("action_items", [])[:5]:
        text += f"- {item.get('task', '')} ({item.get('assignee', 'ne naznachen')})\n"
    async for session in get_db():
        await knowledge_base_service.add_from_meeting(session, result["id"], chat_id, summary)
    await message.answer(text)


@router.message(Command("report"))
async def cmd_report(message: Message):
    report_text = message.text.replace("/report", "").strip()
    if not report_text:
        await message.answer("Ispolzujte: /report <vash otchyot za den>. Primer: /report Segodnya ya sdelal refactoring bazy dannykh i napisal 3 testa.")
        return
    async for session in get_db():
        user_stmt = select(User).where(User.telegram_id == str(message.from_user.id))
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if not user:
            await message.answer("Vy eshche ne zaregistrirovany.")
            return
        chat_id = str(message.chat.id)
        result = await evening_sync_service.process_daily_report(session, user.id, chat_id, report_text)
        user.streak_days += 1
        rewards = await gamification_service.on_daily_report(session, user.id, user.streak_days)
        await session.commit()
        text = f"Otchyot prinyat!\n\n"
        text += f"Zadach zaversheno: {result['tasks_completed']}\n"
        text += f"V rabote: {result['tasks_in_progress']}\n"
        text += f"Status: {result['status']}\n"
        text += f"Strik: {user.streak_days} dnej"
        for reward in rewards:
            if reward["type"] == "achievement":
                ach = reward["data"]["achievement"]
                text += f"\n\n{ach['name']}! (+{ach['xp']} XP)"
        await message.answer(text)


@router.message(Command("wiki"))
async def cmd_wiki(message: Message):
    async for session in get_db():
        chat_id = str(message.chat.id)
        wiki_text = await knowledge_base_service.generate_team_wiki(session, chat_id)
        await message.answer(wiki_text)


@router.message(Command("search"))
async def cmd_search(message: Message):
    query = message.text.replace("/search", "").strip()
    if not query:
        await message.answer("Ispolzujte: /search <zapros>")
        return
    async for session in get_db():
        chat_id = str(message.chat.id)
        results = await knowledge_base_service.search(session, chat_id, query)
        if not results:
            await message.answer("Nichego ne najdeno.")
            return
        text = f"Rezultaty poiska: {query}\n\n"
        for i, entry in enumerate(results[:5], 1):
            text += f"{i}. {entry['title']}\n"
            text += f"{entry['content'][:200]}...\n\n"
        await message.answer(text)


@router.message(Command("leaderboard"))
async def cmd_leaderboard(message: Message):
    async for session in get_db():
        stmt = select(User).where(User.xp > 0).order_by(User.xp.desc()).limit(10)
        result = await session.execute(stmt)
        users = result.scalars().all()
        users_data = []
        for u in users:
            profile = await gamification_service.get_user_profile(session, u.id)
            users_data.append(profile)
        text = gamification_service.get_leaderboard_text(users_data)
        await message.answer(text)


@router.message(Command("achievements"))
async def cmd_achievements(message: Message):
    async for session in get_db():
        user_stmt = select(User).where(User.telegram_id == str(message.from_user.id))
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if not user:
            await message.answer("Vy eshche ne zaregistrirovany.")
            return
        text = "Dostupnye dostizheniya:\n\n"
        for key, ach in gamification_service.achievements.items():
            has_it = key in (user.achievements or [])
            status = "[+]" if has_it else "[ ]"
            text += f"{status} {ach['name']} -- {ach['description']} (+{ach['xp']} XP)\n"
        await message.answer(text)


@router.message(Command("summary_evening"))
async def cmd_summary_evening(message: Message):
    async for session in get_db():
        chat_id = str(message.chat.id)
        result = await evening_sync_service.send_evening_summary(session, chat_id, bot)
        if result.get("missing_reports", 0) > 0:
            missing = await evening_sync_service.check_missing_reports(session, chat_id)
            for m in missing:
                if m.get("telegram_id"):
                    try:
                        await bot.send_message(
                            chat_id=m["telegram_id"],
                            text="Vy ne otpravili ezhednevnyj otchyot! Otpravte /report <vash otchyot>"
                        )
                    except Exception as e:
                        print(f"Failed to notify user: {e}")


@router.message(Command("remind_all"))
async def cmd_remind_all(message: Message):
    async for session in get_db():
        await reminder_service.check_deadlines(session, bot)
        await reminder_service.check_overdue(session, bot)
    await message.answer("Napominaniya otpravleny!")

@router.message(F.chat.type.in_({"group", "supergroup"}))
async def process_group_message(message: Message):
    async for session in get_db():
        tg_user = message.from_user
        user_stmt = select(User).where(User.telegram_id == str(tg_user.id))
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if not user:
            user = User(
                telegram_id=str(tg_user.id),
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name
            )
            session.add(user)
            await session.commit()
        chat_stmt = select(Chat).where(Chat.telegram_chat_id == str(message.chat.id))
        chat_result = await session.execute(chat_stmt)
        chat = chat_result.scalar_one_or_none()
        if not chat:
            chat = Chat(
                telegram_chat_id=str(message.chat.id),
                title=message.chat.title or "Unknown",
                type=message.chat.type
            )
            session.add(chat)
            await session.commit()
        if message.text and len(message.text) > 10:
            task_keywords = ['sdelat', 'nuzhno', 'nado', 'zadacha', 'todo', 'task', 'vzyat', 'srochno', 'deadline', 'dedlajn', 'do', 'k', 'zavtra']
            text_lower = message.text.lower()
            looks_like_task = any(kw in text_lower for kw in task_keywords)
            if looks_like_task:
                extracted = await nlp_engine.extract_tasks(message.text)
                for task_data in extracted.get("tasks", []):
                    if task_data.get("confidence", 0) < 0.5:
                        continue
                    deadline = None
                    if task_data.get("deadline"):
                        try:
                            deadline = datetime.fromisoformat(task_data["deadline"].replace('Z', '+00:00'))
                        except:
                            pass
                    kanban_task = await kanban.create_task(
                        title=task_data["title"],
                        description=task_data.get("description", ""),
                        assignee_id=user.id,
                        deadline=deadline,
                        priority=task_data.get("priority", "medium")
                    )
                    task = Task(
                        yougile_task_id=kanban_task.get("id", ""),
                        title=task_data["title"],
                        description=task_data.get("description", ""),
                        assignee_id=user.id,
                        creator_id=user.id,
                        chat_id=chat.id,
                        deadline=deadline,
                        source="telegram_chat",
                        source_message_id=str(message.message_id),
                        status="todo",
                        confidence_score=task_data.get("confidence", 0.5)
                    )
                    session.add(task)
                    await gamification_service.on_task_created(session, user.id)
                    assignee_name = task_data.get("assignee") or (tg_user.username or tg_user.first_name)
                    deadline_str = f" (do {deadline.strftime('%d.%m %H:%M')})" if deadline else ""
                    await message.reply(
                        f"Zadacha sozdana: {task_data['title']}{deadline_str}\n"
                        f"Otvestvennyj: @{assignee_name}\n"
                        f"Prioritet: {task_data.get('priority', 'medium')}"
                    )
                await session.commit()
        if message.text:
            kb_result = await knowledge_base_service.add_from_chat(
                session, chat.id, message.text, str(message.message_id)
            )
            if kb_result:
                await session.commit()


async def setup_bot():
    dp.include_router(router)
    return bot, dp
