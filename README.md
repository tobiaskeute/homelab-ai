# Homelab AI

Self-hosted AI chat platform for homelab environments with OpenAI-compatible API and LangGraph orchestration.

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│  OpenWebUI  │─────▶│   FastAPI    │─────▶│  LangGraph  │
│  (Frontend) │      │   (Backend)  │      │ Orchestrator│
└─────────────┘      └──────────────┘      └─────────────┘
     :8080                internal            │        |
                                              ▼        ▼
                                             LLMs   Microservices
```

### Components

- **OpenWebUI**: Web interface for chat interactions
- **FastAPI Backend**: OpenAI-compatible API server
  - JWT authentication from OpenWebUI
  - Request routing to LangGraph
  - OpenAI-compatible endpoints (`/v1/models`, `/v1/chat/completions`)
- **LangGraph**: Chat orchestration and workflow management
  - Multi-service routing
  - Context management
  - Response streaming

## Features

- ✅ OpenAI-compatible API
- ✅ JWT-based user authentication
- ✅ Self-hosted, no external dependencies
- 🚧 LangGraph integration (planned)
- 🚧 Multi-LLM support (planned)
- 🚧 Response streaming (planned)

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+

### Installation

1. Clone repository:
```bash
git clone https://github.com/tobiaskeute/homelab-ai
cd homelab-ai
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

3. Start services:
```bash
docker-compose up -d
```

4. Access OpenWebUI:
```
http://localhost:3000
```

## Development

### Project Structure

```
homelab-ai/
├── backend/
│   ├── app.py              # FastAPI application
│   ├── models.py           # Pydantic models
│   ├── routers/
│   │   └── openai.py       # OpenAI-compatible endpoints
│   └── requirements.in     # Python dependencies
├── docker-compose.yml      # Service orchestration
├── .env                    # Environment configuration
└── README.md
```

### Local Development

1. Install dependencies:
```bash
cd backend
pip install -r requirements.txt
```

2. Run backend:
```bash
fastapi dev --host 0.0.0.0
```

3. Access API docs:
```
http://localhost:8000/docs
```

## Roadmap

- [ ] LangGraph integration
- [ ] Multi-LLM backend support (Ollama, vLLM, etc.)
- [ ] Response streaming
- [ ] Chat history persistence
- [ ] RAG capabilities

## Contributing

Contributions welcome. Please open issues for bugs or feature requests.