Архитектура
plain
pm-assistant/

├── docker-compose.yml      # PostgreSQL + Redis + Backend + Celery + Nginx

├── backend/

│   ├── app/

│   │   ├── main.py         # FastAPI + Telegram webhook
│   │   ├── telegram_bot.py # 14 команд бота
│   │   ├── nlp_engine.py   # GPT-4o-mini + fallback regex
│   │   ├── kanban_service.py # YouGile API v2 + mock fallback
│   │   ├── meeting_service.py # Симуляция встреч + Whisper
│   │   ├── reminder_service.py # Дедлайны, просрочки, статусы
│   │   ├── evening_sync.py   # Вечерние отчёты, проверка стриков
│   │   ├── gamification.py   # 12 достижений, 8 уровней, таблица лидеров
│   │   └── knowledge_base.py # База знаний из встреч и чатов
│   └── alembic/            # Миграции БД
├── nginx/                  # Reverse proxy
├── scripts/
│   ├── deploy.sh           # Деплой на сервер
│   └── test.sh             # Проверка работоспособности
└── quickstart.sh           # Быстрый старт
Ключевые фичи
Table
Функция	Реализация
Автозадачи из чата	NLP через OpenAI + fallback regex
Встречи	Симуляция Yandex Telemost с генерацией саммари
Канбан	YouGile API v2 + mock-режим для демо
Напоминания	Celery beat, проверка каждые 5 мин
Вечерняя сводка	Проверка отчётов, теги пропустивших
Геймификация	12 ачивок, 8 уровней, XP, стрик
База знаний	Автоизвлечение решений из встреч
Деплой за 3 шага
bash
# 1. Распаковать на сервере
unzip pm-assistant.zip && cd pm-assistant

# 2. Настроить .env (минимум: TELEGRAM_BOT_TOKEN)
cp .env.example .env
nano .env

# 3. Запустить
./quickstart.sh
Минимальная конфигурация для хакатона
В .env достаточно:
plain
TELEGRAM_BOT_TOKEN=123456:ABC-DEF... (от @BotFather)
OPENAI_API_KEY=sk-... (опционально, есть regex fallback)

Без OpenAI бот работает через regex-извлечение задач. Без YouGile — через mock-канбан.
Демо-сценарий для презентации
Добавить бота в тестовый чат
Написать: "Нужно сделать рефакторинг БД до пятницы, @ivan"
Бот автоматически создаёт задачу в канбане
Команда пишет /meeting
Бот симулирует встречу, генерирует саммари и задачи
Вечером каждый пишет /report Сделал тесты и документацию
Бот проверяет отчёты и шлёт сводку
Технологический стек
Python 3.12 + FastAPI + aiogram 3.x
PostgreSQL 15 + SQLAlchemy 2.0 (async)
Redis + Celery (фоновые задачи)
OpenAI GPT-4o-mini (NLP) / Whisper (распознавание речи)
YouGile API v2 (канбан)
Docker Compose (деплой)


# PM Assistant - AI Project Manager Bot

AI-assistent dlya komandnoj raboty: avtomaticheski sozdayet zadachi iz chata, slushayet vstrechi, vedet kanban i napominayet o dedlajnakh.

## Bystryj start

```bash
# 1. Sklonirujte repozitorij
cd pm-assistant

# 2. Nastrojte okruzhenie
cp .env.example .env
# Otkroyte .env i zapolnite vse API klyuchi

# 3. Zapustite
cd scripts
chmod +x deploy.sh
./deploy.sh
```

## Arhitektura

```
pm-assistant/
├── docker-compose.yml      # Docker orchestration
├── .env.example            # Environment variables template
├── backend/
│   ├── app/
│   │   ├── main.py         # FastAPI + webhook handler
│   │   ├── telegram_bot.py # Bot logic & commands
│   │   ├── nlp_engine.py   # OpenAI GPT-4o-mini NLP
│   │   ├── kanban_service.py # YouGile API integration
│   │   ├── meeting_service.py # Yandex Telemost + Whisper
│   │   ├── reminder_service.py # Proactive reminders
│   │   ├── evening_sync.py   # Daily reports sync
│   │   ├── gamification.py   # RPG system & achievements
│   │   └── knowledge_base.py # Team wiki from meetings
│   ├── Dockerfile
│   └── requirements.txt
├── nginx/
│   └── nginx.conf
└── scripts/
    └── deploy.sh
```

## Funkcional

### Osnovnoj (obyazatel'nyj)
1. **Telegram** - Bot chitaet perepisku, izvlekaet zadachi, dedlajny, otvetstvennykh
2. **Vstrechi** - Demo-simulyaciya Yandex Telemost (s real'nym API - nuzhna avtomatizaciya brauzera)
3. **Kanban** - Integraciya s YouGile (ili mock-doska dlya demo)
4. **Napominaniya** - Avtomaticheskie napominaniya o dedlajnakh i prosrochennykh zadachakh
5. **Vechernyaya svodka** - Proverka otchyotov, svodka po komande

### Dopolnitel'nyj
- **Gamifikaciya** - Urovni, XP, dostizheniya, tablitsa liderov
- **Baza znanij** - Avtomaticheskoe sozdanie iz reshenij i vstrech
- **Lichnyj kabinet** - Profil, statistika, zadachi (/profile)
- **Poisk** - Poisk po baze znanij komandy

## API Endpoints

| Endpoint | Method | Opisanie |
|----------|--------|----------|
| `/` | GET | Status |
| `/health` | GET | Health check |
| `/webhook` | POST | Telegram webhook |
| `/api/tasks` | GET | Spisok zadach |
| `/api/meetings` | GET | Istoriya vstrech |
| `/api/stats` | GET | Statistika |

## Komandy bota

| Komanda | Opisanie |
|---------|----------|
| `/start` | Nachalo raboty |
| `/tasks` | Moi aktivnye zadachi |
| `/task <nazvanie>` | Sozdat zadachu |
| `/done <nazvanie>` | Otmetit vypolnennoj |
| `/profile` | Moj profil i dostizheniya |
| `/meeting` | Nachat demo-vstrechu |
| `/report <tekst>` | Otpravit ezhednevnyj otchyot |
| `/wiki` | Baza znanij komandy |
| `/search <zapros>` | Poisk v baze znanij |
| `/leaderboard` | Tablitsa liderov |
| `/achievements` | Moi dostizheniya |
| `/summary_evening` | Vechernyaya svodka (admin) |
| `/remind_all` | Napomnit vsem (admin) |
| `/help` | Spravka |

## Peremennye okruzheniya

```env
TELEGRAM_BOT_TOKEN=         # Token ot @BotFather
TELEGRAM_WEBHOOK_URL=       # Public URL dlya webhook
YOUGILE_API_KEY=             # API klyuch YouGile
YOUGILE_BOARD_ID=            # ID doski v YouGile
OPENAI_API_KEY=              # Klyuch OpenAI (dlya NLP)
YANDEX_SPEECHKIT_API_KEY=    # Klyuch Yandex SpeechKit
DATABASE_URL=                # URL PostgreSQL
REDIS_URL=                   # URL Redis
SECRET_KEY=                  # Sekretnyj klyuch
```

## Demo-scenarij

1. Dobavit' bota v gruppovoj chat
2. Napisat': "Nuzhno sdelat' refactoring bazy dannyh do pyatnitsy, @username"
3. Bot avtomaticheski sozdaet zadachu v kanbane
4. Komanda pishet: `/meeting`
5. Bot simuliruet vstrechu, generiruet samari i zadachi
6. Kazhdyj vecher otpravlyaet `/report Svoy otchyot`
7. Bot proveryaet otchety i otpravlyaet svodku

## Razvertyvanie na servere

```bash
# SSH na server
git clone <repo>
cd pm-assistant

# Nastrojka
cp .env.example .env
nano .env  # Zapolnite vse klyuchi

# Zapusk
./scripts/deploy.sh

# Proverka statusa
docker-compose ps
docker-compose logs -f backend
```

## Tehnologii

- **Backend**: Python 3.12, FastAPI, aiogram 3.x
- **Baza dannyh**: PostgreSQL 15, SQLAlchemy 2.0, Alembic
- **Cache/Tasks**: Redis, Celery
- **NLP**: OpenAI GPT-4o-mini (s fallback na regex)
- **Raspoznavanie rechi**: OpenAI Whisper / Yandex SpeechKit
- **Kanban**: YouGile API v2 (s mock fallback)
- **Deploy**: Docker, Docker Compose, Nginx
