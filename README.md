# Well-Bot v13 - Voice-First Wellness Assistant

A sophisticated voice-first web application that combines conversational AI with structured wellness activities, built with MCP (Model Context Protocol) architecture.

## 🎯 Project Overview

Well-Bot is a wellness companion that provides:
- **Voice-first interface** with wake-word activation
- **Memory-grounded conversations** using RAG (Retrieval-Augmented Generation)
- **Five core wellness activities**: Journal, Gratitude, To-Do Lists, Spiritual Quotes, and Meditation
- **Safety monitoring** with keyword detection and support resources
- **MCP-enabled** modular tool architecture

## 🏗️ Architecture

### Frontend
- React + Vite web application (Chrome-first)
- Voice interface using Deepgram for streaming STT/TTS
- Three-panel layout: Chat sidebar, conversation history, active chat

### Backend
- FastAPI with MCP tools
- Supabase for authentication, database, and storage
- DeepSeek LLM for chat and tool orchestration
- pgvector for embeddings and semantic search

## 📁 Project Structure

```
Well-Bot_v13/
├── src/
│   ├── backend/
│   │   ├── api/                 # FastAPI routes and endpoints
│   │   ├── core/                # Core business logic
│   │   ├── mcp_tools/           # MCP tool implementations
│   │   │   ├── session/         # Session management tools
│   │   │   ├── safety/          # Safety monitoring tools
│   │   │   ├── memory/          # RAG and memory tools
│   │   │   ├── journal/         # Journal activity tools
│   │   │   ├── gratitude/       # Gratitude activity tools
│   │   │   ├── todo/            # To-do activity tools
│   │   │   ├── quote/           # Spiritual quote tools
│   │   │   └── meditation/      # Meditation activity tools
│   │   ├── services/            # External service integrations
│   │   ├── models/              # Database models
│   │   └── utils/               # Backend utilities
│   ├── frontend/
│   │   ├── components/          # React components
│   │   │   ├── chat/            # Chat interface components
│   │   │   ├── activities/      # Activity-specific components
│   │   │   ├── overlays/        # Modal and overlay components
│   │   │   └── ui/              # Reusable UI components
│   │   ├── pages/               # Page components
│   │   │   ├── chat/            # Chat page
│   │   │   ├── dashboard/       # Dashboard page
│   │   │   └── settings/        # Settings page
│   │   ├── hooks/               # Custom React hooks
│   │   ├── utils/               # Frontend utilities
│   │   └── types/               # TypeScript type definitions
│   └── shared/
│       ├── types/               # Shared type definitions
│       ├── constants/           # Shared constants
│       └── utils/               # Shared utilities
├── tests/
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   └── e2e/                     # End-to-end tests
├── docs/                        # Documentation
├── scripts/                     # Build and deployment scripts
├── config/                      # Configuration files
├── utils/                       # Database schemas and utilities
│   ├── Schema.sql               # New database schema
│   └── Old_Table.sql            # Legacy database schema
├── _Development_Documentation/  # Design documents
├── .env                         # Environment variables
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL with pgvector extension
- Supabase account
- Deepgram API key
- DeepSeek API key

### Installation

1. **Clone and setup environment:**
   ```bash
   cd Well-Bot_v13
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # Linux/Mac
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements-installed.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

4. **Setup database:**
   ```bash
   # Run the schema migration
   psql -f utils/Schema.sql
   ```

5. **Start development server:**
   ```bash
   uvicorn src.backend.api.main:app --reload --port 8000
   ```

## 🔧 Configuration

Key environment variables in `.env`:

- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_ANON_KEY` - Supabase anonymous key
- `DEEPGRAM_API_KEY` - Deepgram API key for speech processing
- `DEEPSEEK_API_KEY` - DeepSeek API key for LLM
- `WB_EMBED_MODEL` - Embedding model (miniLM or e5)
- `WB_WAKE_PHRASE` - Wake word phrase (default: "well-bot")

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

## 📚 Documentation

- [High-Level Design (HLD)](_Development_Documentation/HLD.md)
- [Low-Level Design (LLD)](_Development_Documentation/)
- [Database Schema](utils/Schema.sql)

## 🛡️ Safety & Privacy

- User data isolation with Row Level Security (RLS)
- Safety keyword monitoring with support card interjection
- 30-day log retention policy
- No cross-user data leakage

## 🤝 Contributing

This is a school project. Please refer to the development documentation for architecture decisions and implementation guidelines.

## 📄 License

This project is for educational purposes.
