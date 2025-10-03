# Well-Bot Project Structure Overview

## 📁 Directory Organization

This document provides a detailed overview of the Well-Bot project structure, organized according to modular programming principles and the MCP architecture.

## 🏗️ Architecture Alignment

The project structure aligns with the High-Level Design (HLD) and Low-Level Design (LLD) specifications:

- **MCP Tools**: Each activity (journal, gratitude, todo, quote, meditation) is implemented as a separate MCP tool
- **Modular Design**: Clear separation between frontend, backend, and shared components
- **Voice-First**: Architecture supports streaming STT/TTS and wake-word detection
- **Safety-First**: Dedicated safety monitoring and support systems

## 📂 Detailed Structure

### Backend (`src/backend/`)

#### `api/`
- FastAPI route definitions
- WebSocket endpoints for real-time communication
- REST API endpoints for CRUD operations
- Authentication middleware

#### `core/`
- Business logic and orchestration
- Session state management
- Intent detection and routing
- Topic cache implementation
- Memory/RAG integration

#### `mcp_tools/`
Each subdirectory contains a complete MCP tool implementation:

- **`session/`**: Wake-word detection, session lifecycle management
- **`safety/`**: Keyword monitoring, support card generation
- **`memory/`**: RAG implementation, embedding management
- **`journal/`**: Interactive journal overlay, summarization
- **`gratitude/`**: Single-entry gratitude management
- **`todo/`**: To-do CRUD operations, fuzzy matching
- **`quote/`**: Spiritual quote selection, repeat avoidance
- **`meditation/`**: Video playback, session logging

#### `services/`
- External service integrations (Deepgram, DeepSeek, Supabase)
- Embedding service management
- Audio processing utilities
- Database connection management

#### `models/`
- SQLAlchemy database models
- Pydantic schemas for API validation
- Data transfer objects (DTOs)

#### `utils/`
- Backend utility functions
- Configuration management
- Logging setup
- Error handling

### Frontend (`src/frontend/`)

#### `components/`
- **`chat/`**: Chat interface components, message bubbles, input fields
- **`activities/`**: Activity-specific UI components (cards, widgets)
- **`overlays/`**: Modal dialogs, journal overlay, meditation player
- **`ui/`**: Reusable UI components (buttons, forms, layouts)

#### `pages/`
- **`chat/`**: Main chat interface page
- **`dashboard/`**: User dashboard with activity history
- **`settings/`**: User preferences and configuration

#### `hooks/`
- Custom React hooks for state management
- WebSocket connection hooks
- Audio processing hooks
- Session state hooks

#### `utils/`
- Frontend utility functions
- Audio processing utilities
- State management helpers
- API client functions

#### `types/`
- TypeScript type definitions
- Interface definitions
- Type guards and validators

### Shared (`src/shared/`)

#### `types/`
- Shared type definitions between frontend and backend
- MCP tool contract types
- Common data structures

#### `constants/`
- Application-wide constants
- Configuration values
- Enum definitions

#### `utils/`
- Shared utility functions
- Common validation logic
- Helper functions used by both frontend and backend

### Testing (`tests/`)

#### `unit/`
- Unit tests for individual components
- MCP tool testing
- Utility function testing

#### `integration/`
- Integration tests for API endpoints
- Database integration tests
- External service integration tests

#### `e2e/`
- End-to-end tests for complete user flows
- Voice interaction testing
- Activity workflow testing

### Configuration (`config/`)

- Environment-specific configuration files
- Database configuration
- Service configuration templates

### Scripts (`scripts/`)

- Build and deployment scripts
- Database migration scripts
- Development setup scripts
- Testing automation scripts

### Documentation (`docs/`)

- API documentation
- User guides
- Development guides
- Architecture decision records

## 🔄 Data Flow

### Voice Interaction Flow
1. **Wake-word Detection** → `src/backend/mcp_tools/session/`
2. **Speech-to-Text** → `src/backend/services/` (Deepgram)
3. **Intent Detection** → `src/backend/core/`
4. **MCP Tool Execution** → `src/backend/mcp_tools/[activity]/`
5. **Response Generation** → `src/backend/core/`
6. **Text-to-Speech** → `src/backend/services/` (Deepgram)
7. **UI Update** → `src/frontend/components/`

### Memory/RAG Flow
1. **User Input** → `src/backend/core/`
2. **Memory Search** → `src/backend/mcp_tools/memory/`
3. **Embedding Query** → `src/backend/services/`
4. **Context Retrieval** → Database via `src/backend/models/`
5. **LLM Processing** → `src/backend/services/` (DeepSeek)
6. **Response Generation** → `src/backend/core/`

## 🛡️ Security Considerations

- **Row Level Security (RLS)**: Implemented at database level
- **User Isolation**: All data access filtered by `user_id`
- **Safety Monitoring**: Continuous keyword monitoring across all activities
- **API Security**: Authentication and authorization middleware

## 📊 Monitoring & Observability

- **Structured Logging**: Using `structlog` for consistent log formatting
- **Performance Metrics**: Latency tracking for all operations
- **Error Tracking**: Comprehensive error logging and monitoring
- **User Analytics**: Activity tracking and usage patterns

## 🚀 Deployment Considerations

- **Environment Configuration**: Separate configs for dev/staging/prod
- **Database Migrations**: Automated schema updates
- **Service Dependencies**: External service health checks
- **Scaling**: Designed for horizontal scaling with stateless services

This structure provides a solid foundation for implementing the Well-Bot MVP while maintaining clean separation of concerns and supporting future extensibility.
