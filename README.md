# Jarvis AI OS

An intelligent, modular AI assistant inspired by Iron Man's Jarvis. Built with Python, React, and OpenAI.

## Architecture

Jarvis follows Hexagonal (Ports & Adapters) Architecture with Clean Architecture principles.

### Core Principles
- **SOLID** — Single Responsibility, Open/Closed, Liskov, Interface Segregation, Dependency Inversion
- **Clean Architecture** — Domain logic is independent of frameworks, UI, and databases
- **Security First** — All destructive operations require explicit confirmation
- **Modular** — Plugin system for extensibility without modifying core

### System Layers

```
Presentation  │  REST API / WebSocket / CLI
──────────────┼─────────────────────────────
Application   │  Use Cases / Orchestrators
──────────────┼─────────────────────────────
Domain        │  Entities / Value Objects / Interfaces
──────────────┼─────────────────────────────
Infrastructure│  PostgreSQL / Redis / OpenAI / Whisper / TTS
```

### Component Diagram

```
┌───────────────────────────────────────────────────┐
│              React + Electron Desktop App           │
│  ┌─────────┐ ┌──────┐ ┌──────┐ ┌──────────────┐  │
│  │  Chat   │ │Voice │ │Files │ │  Automation   │  │
│  └────┬────┘ └──┬───┘ └──┬───┘ └──────┬───────┘  │
│       └─────────┴────────┴────────────┘           │
└───────────────────┬───────────────────────────────┘
                    │ WebSocket / REST
┌───────────────────┴───────────────────────────────┐
│              API Gateway (FastAPI)                  │
│  ┌─────────────────────────────────────────────┐  │
│  │            Core Orchestrator                 │  │
│  │  ┌───────┐ ┌───────┐ ┌───────┐ ┌────────┐  │  │
│  │  │Agent  │ │Memory │ │Tool   │ │Task    │  │  │
│  │  │Router │ │Manager│ │Registry│ │Planner │  │  │
│  │  └───┬───┘ └───┬───┘ └───┬───┘ └────┬───┘  │  │
│  └──────┼─────────┼─────────┼──────────┼──────┘  │
└─────────┼─────────┼─────────┼──────────┼──────────┘
          │         │         │          │
┌─────────┴─────────┴─────────┴──────────┴──────────┐
│                Infrastructure Layer                 │
│  ┌──────────┐ ┌──────┐ ┌─────────┐ ┌───────────┐ │
│  │PostgreSQL│ │Redis │ │pgvector │ │Docker      │ │
│  │+pgvector │ │Cache │ │(embeds) │ │Containers  │ │
│  └──────────┘ └──────┘ └─────────┘ └───────────┘ │
└───────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Clone and enter
cd jarvis

# Start all services
docker-compose up -d

# Run backend
cd backend && poetry install && poetry run uvicorn app.main:app --reload

# Run frontend
cd frontend && npm install && npm run dev
```

## Development Phases

| Phase | Features | Status |
|-------|----------|--------|
| 1     | Auth, Chat, Memory, Voice | 🚧 In Progress |
| 2     | Files, Browser, Calendar, Email, Automation | 📋 Planned |
| 3     | Multi-Agent, Local LLM, Vision, Autonomous | 📋 Planned |

## Tech Stack

- **Backend**: Python 3.12, FastAPI, OpenAI API
- **Database**: PostgreSQL 16 + pgvector + Redis 7
- **Frontend**: React 18, TypeScript, Electron
- **Voice**: OpenAI Whisper (STT) + ElevenLabs/OpenAI TTS
- **Deployment**: Docker, Docker Compose
