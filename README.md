# FinTrack

A modern full-stack financial tracking application that combines automated email processing with manual expense management. Built with FastAPI backend and React frontend, featuring Gmail integration for automatic transaction processing, intelligent document parsing, and a credit-based subscription system.

## Product Images
<img width="2544" height="1272" alt="Screenshot 2025-11-16 at 6 36 42 PM" src="https://github.com/user-attachments/assets/60ae443b-0b86-47a2-bda2-a9c46321114b" />

<img width="2557" height="1272" alt="Screenshot 2025-11-16 at 6 36 51 PM" src="https://github.com/user-attachments/assets/eae47f6e-9dc0-468e-8d1c-7ed5ff297f56" />

<img width="2557" height="1272" alt="Screenshot 2025-11-16 at 6 36 58 PM" src="https://github.com/user-attachments/assets/8a730d14-4549-4c63-bcfa-bbeedca75297" />

<img width="2557" height="1272" alt="Screenshot 2025-11-16 at 6 37 06 PM" src="https://github.com/user-attachments/assets/e4e1a393-ce05-45fe-87c5-87dabba70a9b" />


## Features

- **Manual Expense Tracking** — Add, edit, and categorize expenses
- **Gmail Integration** — Auto-import receipts via OAuth
- **AI Document Processing** — Extract data from PDFs and images using OpenAI
- **Credit System** — 100 free credits on signup
- **Background Jobs** — Scheduled email sync and processing

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Backend | FastAPI, PostgreSQL, SQLAlchemy, Alembic, APScheduler |
| Frontend | React 18, TypeScript, Vite, Redux Toolkit, Tailwind, Shadcn/ui |
| Integrations | Google OAuth, AWS S3, OpenAI |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL
- Docker (optional)

### Using Docker

```bash
docker-compose up -d
```

### Manual Setup

```bash
# Backend
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/fintrack

# Auth
JWT_SECRET=your-secret
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# AWS
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
S3_BUCKET_NAME=your-bucket

# OpenAI
OPENAI_API_KEY=your-key

# URLs
FRONTEND_URL=http://localhost:8080
VITE_API_BASE_URL=http://localhost:8000/api
```

## Project Structure

```
app/
├── main.py                     # FastAPI entry + scheduler
├── controller/
│   └── controller.py           # Request handlers (User, Expense, File, Email)
├── services/
│   ├── db_service.py           # Database operations
│   ├── gmail_service.py        # Gmail API integration
│   ├── subscription_service.py # Credit & billing logic
│   ├── s3_service.py           # AWS S3 file storage
│   ├── jwt_service.py          # JWT token handling
│   ├── token_service.py        # OAuth token refresh
│   ├── file_service.py         # File processing
│   ├── cron_service.py         # Scheduled jobs
│   ├── integration_service.py  # Multi-provider integrations
│   ├── email_attachment_service.py
│   └── llm/
│       └── service.py          # OpenAI document analysis
├── models/
│   ├── models.py               # SQLAlchemy ORM models
│   └── schema.py               # Pydantic request/response schemas
├── routes/
│   └── routes.py               # API endpoint definitions
├── middleware/
│   └── middleware.py           # Auth & request tracking
├── utils/
│   ├── exception_handlers.py   # Centralized error handling
│   └── oauth.py                # OAuth utilities
└── migrations/                 # Alembic database migrations

frontend/
├── src/
│   ├── components/
│   │   ├── ui/                 # Shadcn/ui components
│   │   ├── dashboard/          # Dashboard widgets
│   │   ├── expense/            # Expense management
│   │   └── layout/             # App layout (Header, Sidebar)
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── Expenses.tsx
│   │   ├── Settings.tsx
│   │   └── Upload.tsx
│   ├── lib/
│   │   └── api.ts              # API client
│   ├── store/
│   │   ├── store.ts            # Redux store config
│   │   └── slices/             # Redux slices (auth, expense, etc.)
│   ├── hooks/                  # Custom React hooks
│   └── types/                  # TypeScript definitions
├── vite.config.ts
└── tailwind.config.js
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/login` | GET | Google OAuth login |
| `/api/emails/oauth2callback` | GET | OAuth callback |
| `/api/expense` | GET | List expenses |
| `/api/expense` | POST | Create expense |
| `/api/expense/{id}` | PUT | Update expense |
| `/api/expense/{id}` | DELETE | Delete expense |
| `/api/emails` | POST | Trigger email sync |
| `/api/upload` | POST | Upload PDF/image |
| `/api/user` | GET | Get user profile |
| `/api/user` | PUT | Update profile |
| `/api/user/settings` | GET | Get integrations & credits |

## Database Schema

**Tables:** `users`, `expenses`, `sources`, `emails`, `attachments`, `processed_email_data`, `subscriptions`, `plans`, `features`, `credit_history`, `integrations`

```bash
# Run migrations
cd app && alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"
```

## Credit System

| Action | Credits |
|--------|---------|
| Gmail Sync | 1 |
| Email Processing | 1 |
| PDF Upload | 2 |
| LLM Processing | 3 |

New users receive 100 credits with a 30-day trial.

## Architecture

```
Request → Middleware (JWT) → Routes → Controller → Services → Database
                                          ↓
                                    S3 / OpenAI / Gmail
```

### Background Jobs (APScheduler)

| Job | Frequency |
|-----|-----------|
| Gmail Sync | Every 6 hours |
| Token Refresh | Every 1 hour |
| Email Processing | Every 6 hours |

## License

MIT