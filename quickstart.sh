#!/bin/bash
set -e

echo "=== PM Assistant Quick Start ==="

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Docker ne ustanovlen. Ustanovka..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "Perezagruzite terminal i zapustite skript snova"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose ne ustanovlen. Ustanovka..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Setup env
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "=== Nastrojte .env file ==="
    echo "1. Poluchite token bota u @BotFather"
    echo "2. Ustanovite TELEGRAM_BOT_TOKEN"
    echo "3. (Opcionalno) Ustanovite OPENAI_API_KEY dlya uluchshennogo NLP"
    echo "4. (Opcionalno) Ustanovite YOUGILE_API_KEY dlya realnoj integracii"
    echo ""
    echo "Dlya demo-raboty dostatochno tol'ko TELEGRAM_BOT_TOKEN"
    echo ""
    read -p "Nazhmite Enter dlya otkrytiya .env v redaktore..."
    nano .env || vi .env || ${EDITOR:-nano} .env
fi

# Create directories
mkdir -p data/recordings nginx/ssl

# Build and start
echo ""
echo "=== Zapusk servisov ==="
docker-compose down 2>/dev/null || true
docker-compose up --build -d

echo ""
echo "=== Ozhidanie zapuska bazy dannyh ==="
sleep 15

echo "=== Zapusk migracij ==="
docker-compose exec -T backend alembic upgrade head 2>/dev/null || echo "Migracii uje zapuscheny ili oshibka (ne kritichno dlya demo)"

echo ""
echo "=== Ustanovka webhook ==="
BOT_TOKEN=$(grep TELEGRAM_BOT_TOKEN .env | cut -d '=' -f2)
if [ -n "$BOT_TOKEN" ] && [ "$BOT_TOKEN" != "your_telegram_bot_token_from_BotFather" ]; then
    curl -s "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook?url=${TELEGRAM_WEBHOOK_URL:-http://localhost:8000/webhook}" || echo "Webhook ne ustanovlen - proverte token"
fi

echo ""
echo "========================================"
echo "  PM Assistant zapuschen!"
echo "========================================"
echo ""
echo "API:        http://localhost:8000"
echo "Health:     http://localhost:8000/health"
echo "Webhook:    http://localhost:8000/webhook"
echo ""
echo "Komandy dlya upravleniya:"
echo "  docker-compose logs -f backend   # Smotret logi"
echo "  docker-compose ps                 # Status servisov"
echo "  docker-compose down               # Ostanovit"
echo "  docker-compose restart backend    # Perezapusk"
echo ""
echo "Testovye komandy v Telegram:"
echo "  /start     - Nachalo"
echo "  /meeting   - Demo vstrechi"
echo "  /help      - Vse komandy"
echo ""
echo "Dobavte bota v gruppovoj chat i napishte:"
echo "  Nuzhno sdelat' refactoring bazy dannyh do pyatnitsy"
echo ""
