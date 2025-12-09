#!/bin/bash

# TenChat NeuroBooster Startup Script (Linux/Mac)

echo "==================================="
echo "TenChat NeuroBooster v1.0"
echo "==================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "Creating from .env.example..."
    cp .env.example .env
    echo "✅ .env created. Please edit it and add your AI_API_KEY"
    echo ""
    read -p "Press Enter to continue after editing .env..."
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed!"
    echo "Please install Docker from: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed!"
    echo "Please install Docker Compose from: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "🚀 Starting TenChat NeuroBooster..."
echo ""

# Create directories if they don't exist
mkdir -p data logs

# Start Docker Compose
docker-compose up -d

# Check if containers started successfully
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ TenChat NeuroBooster started successfully!"
    echo ""
    echo "📊 Access points:"
    echo "   UI:  http://localhost:8501"
    echo "   API: http://localhost:8000"
    echo "   API Docs: http://localhost:8000/docs"
    echo ""
    echo "📝 Useful commands:"
    echo "   View logs:    docker-compose logs -f"
    echo "   Stop service: docker-compose down"
    echo "   Restart:      docker-compose restart"
    echo ""
else
    echo ""
    echo "❌ Failed to start containers!"
    echo "Check logs: docker-compose logs"
    exit 1
fi
