#!/bin/bash
# NYAYASHASTRA Quick Deployment Script

echo "🏛️  NYAYASHASTRA Deployment Script"
echo "=================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://www.docker.com/get-started"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "📝 Creating .env file from template..."
    
    cat > .env << 'EOF'
# Backend Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,http://localhost

# Database
DATABASE_URL=sqlite:///./nyayguru.db

# Vector Database
CHROMA_PERSIST_DIR=./chroma_db
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

# AI/LLM Configuration (Add your API keys)
GEMINI_API_KEY=
OPENAI_API_KEY=
GROQ_API_KEY=

# Local LLM
USE_LOCAL_LLM=false
LOCAL_LLM_ENDPOINT=http://localhost:11434/api

# Security
SECRET_KEY=$(openssl rand -hex 32)

# Frontend Configuration
VITE_API_URL=http://localhost:8000
VITE_CLERK_PUBLISHABLE_KEY=pk_test_YXBwYXJlbnQtdHJvdXQtNTAuY2xlcmsuYWNjb3VudHMuZGV2JA
EOF
    
    echo "✅ .env file created!"
    echo "⚠️  IMPORTANT: Edit .env and add your API keys before deploying to production"
    echo ""
fi

# Prompt for deployment type
echo "Select deployment option:"
echo "1) Development (with hot reload)"
echo "2) Production (optimized build)"
echo "3) Stop all services"
echo "4) View logs"
echo "5) Rebuild from scratch"
read -p "Enter option (1-5): " option

case $option in
    1)
        echo "🚀 Starting in DEVELOPMENT mode..."
        docker-compose up --build
        ;;
    2)
        echo "🚀 Starting in PRODUCTION mode..."
        docker-compose up -d --build
        echo ""
        echo "✅ Services started successfully!"
        echo ""
        echo "📍 Access points:"
        echo "   Frontend:  http://localhost"
        echo "   Backend:   http://localhost:8000"
        echo "   API Docs:  http://localhost:8000/docs"
        echo ""
        echo "📊 Check status: docker-compose ps"
        echo "📋 View logs:    docker-compose logs -f"
        echo "🛑 Stop:         docker-compose down"
        ;;
    3)
        echo "🛑 Stopping all services..."
        docker-compose down
        echo "✅ All services stopped"
        ;;
    4)
        echo "📋 Viewing logs (Ctrl+C to exit)..."
        docker-compose logs -f
        ;;
    5)
        echo "🔄 Rebuilding from scratch..."
        docker-compose down -v
        docker-compose build --no-cache
        docker-compose up -d
        echo "✅ Rebuild complete!"
        ;;
    *)
        echo "❌ Invalid option"
        exit 1
        ;;
esac
