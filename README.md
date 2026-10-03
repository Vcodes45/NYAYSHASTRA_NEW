# 🏛️ NYAYASHASTRA - AI Legal Assistant for India

> **Intelligent Legal Research Platform powered by Multi-Agent RAG System**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/react-18+-blue.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.109+-green.svg)](https://fastapi.tiangolo.com/)

---

## 📋 Overview

NYAYASHASTRA is a production-grade AI-powered legal research assistant designed specifically for Indian law. It provides precise, verifiable legal answers with proper citations through an advanced multi-agent RAG (Retrieval-Augmented Generation) system.

### ✨ Key Features

- 🤖 **Multi-Agent Architecture** - Orchestrated agents for query understanding, statute retrieval, case law research, and response synthesis
- 🔍 **Hybrid Search** - Combines semantic search (BGE-M3) with keyword search (BM25) for optimal retrieval
- 📚 **Comprehensive Coverage** - Indian statutes, case laws, regulations across multiple domains
- 🌐 **Bilingual Support** - English and Hindi language support
- ✅ **Citation Verification** - Automatic citation validation and source verification
- 🎯 **Domain-Specific** - Criminal, Civil, Corporate, Constitutional, IT/Cyber, and more
- 🔐 **Secure Authentication** - Clerk-based user authentication
- 📱 **Responsive UI** - Modern React frontend with Tailwind CSS and shadcn/ui

---

## 🚀 Quick Start

**⚡ New to this project? See [QUICKSTART.md](QUICKSTART.md) for a 5-minute setup guide!**

### Option 1: Docker (Recommended) - 2 Minutes

```bash
# Clone repository
git clone https://github.com/SatyamPandey-07/NYAYASHASTRA.git
cd NYAYASHASTRA

# Run deployment script (Windows)
.\deploy.ps1

# OR Mac/Linux
chmod +x deploy.sh
./deploy.sh

# Access the application
# Frontend: http://localhost
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Option 2: Manual Setup - 10 Minutes

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
npm install
npm run dev
```

### Option 3: Using Makefile (Linux/Mac/WSL)

```bash
make install    # Install all dependencies
make dev        # Start development servers
make docker-up  # Start with Docker
make help       # See all commands
```

---

## 📦 Tech Stack

### Backend
- **Framework:** FastAPI (Python 3.10+)
- **Database:** SQLite (dev) / PostgreSQL (prod)
- **Vector DB:** ChromaDB
- **Embeddings:** BGE-M3 (multilingual)
- **LLM:** OpenAI GPT-4 / Groq LLaMA / Local Ollama
- **Search:** Hybrid (Semantic + BM25)
- **Reranking:** BGE Reranker v2-m3

### Frontend
- **Framework:** React 18 + TypeScript
- **Build Tool:** Vite
- **Styling:** Tailwind CSS
- **UI Components:** shadcn/ui + Radix UI
- **3D Visuals:** Three.js + React Three Fiber
- **State:** React Query (TanStack Query)
- **Auth:** Clerk
- **Routing:** React Router v6

---

## 🏗️ Project Structure

```
NYAYASHASTRA/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── agents/         # Multi-agent system
│   │   ├── routes/         # API endpoints
│   │   ├── services/       # Business logic
│   │   ├── models.py       # Database models
│   │   └── main.py         # FastAPI app
│   ├── data/               # Legal documents
│   ├── chroma_db/          # Vector database
│   ├── scripts/            # Data ingestion
│   └── requirements.txt
│
├── src/                    # React frontend
│   ├── components/         # UI components
│   ├── pages/              # Route pages
│   ├── hooks/              # Custom hooks
│   ├── services/           # API services
│   └── main.tsx            # App entry
│
├── docker-compose.yml      # Docker orchestration
├── DEPLOYMENT.md           # Deployment guide
└── README.md               # This file
```

---

## 🚢 Deployment

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for comprehensive deployment instructions including:

- 🐳 **Docker deployment** (easiest)
- ☁️ **Cloud platforms** (Railway, Render, Vercel, DigitalOcean, AWS)
- 🛠️ **Manual deployment** (production setup)
- 🔐 **Environment configuration**
- 📊 **Performance optimization**

### Quick Deploy Options

| Platform | Difficulty | Setup Time | Cost |
|----------|-----------|------------|------|
| **Railway.app** | ⭐ Very Easy | 5 min | $5-20/mo |
| **Render.com** | ⭐⭐ Easy | 10 min | Free-$7/mo |
| **Docker Local** | ⭐⭐ Easy | 5 min | Free |
| **Vercel + Render** | ⭐⭐ Easy | 15 min | Free-$7/mo |
| **DigitalOcean** | ⭐⭐⭐ Medium | 30 min | $10-25/mo |

---

## 🔧 Configuration

### Backend Environment Variables

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173

# Database
DATABASE_URL=sqlite:///./nyayguru.db

# AI/LLM (Choose one)
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...
USE_LOCAL_LLM=false

# Vector Database
CHROMA_PERSIST_DIR=./chroma_db
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

### Frontend Environment Variables

```bash
VITE_API_URL=http://localhost:8000
VITE_CLERK_PUBLISHABLE_KEY=pk_test_...
```

---

## 🎯 Features in Detail

### 1. Multi-Agent RAG System

- **Query Agent** - Understands legal queries, detects language and intent
- **Statute Agent** - Retrieves relevant Indian statutes and acts
- **Case Law Agent** - Finds precedent cases and judgments
- **Regulatory Agent** - Filters by jurisdiction and domain
- **Citation Agent** - Validates citations and sources
- **Response Agent** - Synthesizes comprehensive legal answers
- **Orchestrator** - Coordinates all agents intelligently

### 2. Advanced Search

- **Hybrid Retrieval** - Combines vector similarity and keyword matching
- **Reranking** - Uses BGE Reranker for precision
- **Multi-lingual** - Handles English and Hindi queries
- **Domain Filtering** - Criminal, Civil, Corporate, etc.

### 3. User Interface

- **Chat Interface** - Interactive legal Q&A
- **Document Upload** - Analyze legal documents
- **Citation Viewer** - View source documents and citations
- **Lawyer Booking** - Connect with legal professionals
- **IPC/BNS Comparison** - Compare old IPC with new BNS

---

## 📚 Documentation

- [Backend Documentation](backend/README.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Hybrid RAG Architecture](docs/HYBRID_RAG_ARCHITECTURE.md)
- [Booking Feature](docs/BOOKING_FEATURE.md)

---

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
npm run test
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Indian Legal System** - All legal content is publicly available
- **LangChain** - RAG framework
- **ChromaDB** - Vector database
- **BGE Models** - State-of-the-art embeddings
- **FastAPI** - Modern Python web framework
- **React ecosystem** - Frontend libraries

---

## 📞 Support

For issues, questions, or contributions:

- **GitHub Issues:** [Report a bug or request a feature](https://github.com/SatyamPandey-07/NYAYASHASTRA/issues)
- **Email:** Support contact (if available)
- **Documentation:** Check [DEPLOYMENT.md](DEPLOYMENT.md) for deployment help

---

## 🗺️ Roadmap

- [ ] Mobile app (React Native)
- [ ] Voice input support
- [ ] More regional languages
- [ ] Advanced analytics dashboard
- [ ] Legal document generator
- [ ] Integration with court websites
- [ ] Collaborative research features

---

**Built with ❤️ for India's legal community** 🇮🇳

---

## ⚖️ Disclaimer

This tool is for informational and educational purposes only. It does not constitute legal advice. Always consult with a qualified legal professional for specific legal matters.

---

© 2026 NYAYASHASTRA | AI-Powered Legal Research Platform
