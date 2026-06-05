#!/bin/bash
set -e

echo "=== PM Assistant Deployment ==="

# Check prerequisites
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Create .env if not exists
if [ ! -f .env ]; then
    echo "Creating .env from example..."
    cp .env.example .env
    echo "WARNING: Please edit .env file with your actual API keys before running!"
    exit 1
fi

# Create data directories
mkdir -p data/recordings
mkdir -p nginx/ssl

# Build and start
echo "Building and starting services..."
docker-compose down 2>/dev/null || true
docker-compose pull
docker-compose up --build -d

# Wait for DB
echo "Waiting for database..."
sleep 10

# Run migrations
echo "Running database migrations..."
docker-compose exec -T backend alembic upgrade head

echo ""
echo "=== Deployment Complete ==="
echo "API: http://localhost:8000"
echo "Health: http://localhost:8000/health"
echo "Webhook: http://localhost:8000/webhook"
echo ""
echo "Don't forget to:"
echo "1. Set TELEGRAM_WEBHOOK_URL in .env to your public URL"
echo "2. Set TELEGRAM_BOT_TOKEN from @BotFather"
echo "3. Configure YouGile API keys"
echo "4. Set up SSL certificates in nginx/ssl/"
