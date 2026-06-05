import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from aiogram import Bot
from aiogram.types import Update

from app.config import get_settings
from app.models import init_db, engine, Base
from app.telegram_bot import setup_bot

settings = get_settings()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = None
dp = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot, dp

    # Initialize database
    init_db(settings.DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Setup bot
    bot, dp = await setup_bot()

    # Set webhook
    if settings.TELEGRAM_WEBHOOK_URL:
        await bot.set_webhook(settings.TELEGRAM_WEBHOOK_URL)
        logger.info(f"Webhook set to {settings.TELEGRAM_WEBHOOK_URL}")

    yield

    # Cleanup
    if bot:
        await bot.session.close()


app = FastAPI(title="PM Assistant API", lifespan=lifespan)


@app.get("/")
async def root():
    return {"status": "ok", "service": "PM Assistant Bot"}


@app.get("/health")
async def health():
    return {"status": "healthy", "bot_connected": bot is not None}


@app.post("/webhook")
async def webhook(request: Request):
    if not bot or not dp:
        return JSONResponse({"error": "Bot not initialized"}, status_code=503)

    try:
        data = await request.json()
        update = Update.model_validate(data)
        await dp.feed_update(bot=bot, update=update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return JSONResponse({"error": str(e)}, status_code=400)


@app.get("/api/tasks")
async def list_tasks():
    from app.kanban_service import get_kanban_service
    kanban = get_kanban_service()
    tasks = await kanban.get_tasks()
    return {"tasks": tasks}


@app.get("/api/meetings")
async def list_meetings():
    import os
    import json
    recordings_dir = "/app/data/recordings"
    meetings = []
    if os.path.exists(recordings_dir):
        for f in os.listdir(recordings_dir):
            if f.endswith(".json"):
                with open(os.path.join(recordings_dir, f), "r") as file:
                    meetings.append(json.load(file))
    return {"meetings": meetings}


@app.get("/api/stats")
async def get_stats():
    from sqlalchemy import select, func
    from app.models import User, Task, Chat

    async with engine.connect() as conn:
        user_count = await conn.execute(select(func.count()).select_from(User))
        task_count = await conn.execute(select(func.count()).select_from(Task))
        chat_count = await conn.execute(select(func.count()).select_from(Chat))

        return {
            "users": user_count.scalar(),
            "tasks": task_count.scalar(),
            "chats": chat_count.scalar()
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
