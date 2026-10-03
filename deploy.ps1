# NYAYASHASTRA Quick Deployment Script (Windows)
# Run with: .\deploy.ps1

Write-Host "NYAYASHASTRA Deployment Script" -ForegroundColor Cyan
Write-Host "=================================="
Write-Host ""

# Check if Docker is installed
try {
    $null = docker --version
    Write-Host "SUCCESS: Docker is installed" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker is not installed. Please install Docker Desktop first." -ForegroundColor Red
    Write-Host "Visit: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

# Check if Docker Compose is available
try {
    $null = docker-compose --version
    Write-Host "SUCCESS: Docker Compose is installed" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker Compose is not installed." -ForegroundColor Red
    exit 1
}

Write-Host ""

# Check if .env file exists
if (-not (Test-Path .env)) {
    Write-Host "WARNING: .env file not found!" -ForegroundColor Yellow
    Write-Host "Creating .env file from template..." -ForegroundColor Cyan
    
    $envContent = "# Backend Configuration`nAPI_HOST=0.0.0.0`nAPI_PORT=8000`nAPI_DEBUG=false`nCORS_ORIGINS=http://localhost:5173`n`n# Database`nDATABASE_URL=sqlite:///./nyayguru.db`n`n# Vector Database`nCHROMA_PERSIST_DIR=./chroma_db`nEMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`n`n# AI/LLM Configuration`nGEMINI_API_KEY=`nOPENAI_API_KEY=`nGROQ_API_KEY=`n`n# Local LLM`nUSE_LOCAL_LLM=false`nLOCAL_LLM_ENDPOINT=http://localhost:11434/api`n`n# Security`nSECRET_KEY=nyayashastra-secret-key-change-in-production-min-32-chars`n`n# Frontend Configuration`nVITE_API_URL=http://localhost:8000`nVITE_CLERK_PUBLISHABLE_KEY=pk_test_YXBwYXJlbnQtdHJvdXQtNTAuY2xlcmsuYWNjb3VudHMuZGV2JA"
    
    Set-Content -Path .env -Value $envContent
    Write-Host "SUCCESS: .env file created!" -ForegroundColor Green
    Write-Host "IMPORTANT: Edit .env and add your API keys before deploying to production" -ForegroundColor Yellow
    Write-Host ""
}

# Prompt for deployment type
Write-Host "Select deployment option:" -ForegroundColor Cyan
Write-Host "1 - Development with hot reload"
Write-Host "2 - Production optimized build"
Write-Host "3 - Stop all services"
Write-Host "4 - View logs"
Write-Host "5 - Rebuild from scratch"
Write-Host "6 - Open in browser"
$option = Read-Host "Enter option (1-6)"

switch ($option) {
    "1" {
        Write-Host "Starting in DEVELOPMENT mode..." -ForegroundColor Green
        docker-compose up --build
    }
    "2" {
        Write-Host "Starting in PRODUCTION mode..." -ForegroundColor Green
        docker-compose up -d --build
        Write-Host ""
        Write-Host "Services started successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Access points:" -ForegroundColor Cyan
        Write-Host "   Frontend:  http://localhost"
        Write-Host "   Backend:   http://localhost:8000"
        Write-Host "   API Docs:  http://localhost:8000/docs"
        Write-Host ""
        Write-Host "Check status: docker-compose ps" -ForegroundColor Yellow
        Write-Host "View logs:    docker-compose logs -f" -ForegroundColor Yellow
        Write-Host "Stop:         docker-compose down" -ForegroundColor Yellow
    }
    "3" {
        Write-Host "Stopping all services..." -ForegroundColor Yellow
        docker-compose down
        Write-Host "All services stopped" -ForegroundColor Green
    }
    "4" {
        Write-Host "Viewing logs (Ctrl+C to exit)..." -ForegroundColor Cyan
        docker-compose logs -f
    }
    "5" {
        Write-Host "Rebuilding from scratch..." -ForegroundColor Yellow
        docker-compose down -v
        docker-compose build --no-cache
        docker-compose up -d
        Write-Host "Rebuild complete!" -ForegroundColor Green
    }
    "6" {
        Write-Host "Opening in browser..." -ForegroundColor Cyan
        Start-Process "http://localhost"
        Start-Process "http://localhost:8000/docs"
    }
    default {
        Write-Host "Invalid option" -ForegroundColor Red
        exit 1
    }
}
