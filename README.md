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
