# FinTrack

A modern full-stack financial tracking application that combines automated email processing with manual expense management. Built with FastAPI backend and React frontend, featuring Gmail integration for automatic transaction processing, intelligent document parsing, and a credit-based subscription system.

## Product Images
<img width="2544" height="1272" alt="Screenshot 2025-11-16 at 6 36 42 PM" src="https://github.com/user-attachments/assets/60ae443b-0b86-47a2-bda2-a9c46321114b" />

<img width="2557" height="1272" alt="Screenshot 2025-11-16 at 6 36 51 PM" src="https://github.com/user-attachments/assets/eae47f6e-9dc0-468e-8d1c-7ed5ff297f56" />

<img width="2557" height="1272" alt="Screenshot 2025-11-16 at 6 36 58 PM" src="https://github.com/user-attachments/assets/8a730d14-4549-4c63-bcfa-bbeedca75297" />

<img width="2557" height="1272" alt="Screenshot 2025-11-16 at 6 37 06 PM" src="https://github.com/user-attachments/assets/e4e1a393-ce05-45fe-87c5-87dabba70a9b" />

### 🔧 Architecture Overview

#### **Entry Point (`main.py`)**
- FastAPI application initialization with lifespan management
- CORS middleware configuration
- APScheduler setup for background jobs
- Centralized exception handler registration
- Health check endpoints

#### **Controllers (`controller/`)**
- Request/response handling and validation
- Business logic coordination between services
- Input sanitization and output formatting
- Error handling and HTTP status management

#### **Services Layer (`services/`)**
- **Core Services:**
  - `subscription_service.py`: Credit-based billing, plan management, feature validation
  - `gmail_service.py`: Gmail API integration, email fetching, OAuth handling
  - `user_service.py`: User profile management, authentication logic
  - `db_service.py`: Database operations, query optimization, transaction management

- **Integration Services:**
  - `integration_service.py`: Multi-provider integration framework
  - `email_attachment_service.py`: Email attachment processing and extraction
  - `llm_service.py`: AI-powered document analysis and data extraction
  - `s3_service.py`: AWS S3 file storage and retrieval

- **Utility Services:**
  - `jwt_service.py`: JWT token creation and validation
  - `token_service.py`: OAuth token refresh and management
  - `file_service.py`: File processing and metadata extraction
  - `cron_service.py`: Scheduled job definitions and execution

#### **Models (`models/`)**
- SQLAlchemy ORM models with relationships
- Enum definitions for status and types
- Database indexes and constraints
- Mixins for common functionality (timestamps, soft delete)

#### **Routes (`routes/`)**
- RESTful API endpoint definitions
- Request/response models with Pydantic
- Authentication and authorization decorators
- API documentation with FastAPI automatic schema generation

#### **Middleware (`middleware/`)**
- JWT authentication validation
- Request ID generation for tracing
- Cross-cutting concerns like logging and monitoring

#### **Utils (`utils/`)**
- Custom exception classes and handlers
- OAuth flow utilities
- Common helper functions
- Configuration management

### 🔄 Data Flow Architecture

```
HTTP Request
    ↓
Middleware (Auth, Request ID)
    ↓
Routes (FastAPI Router)
    ↓
Controller (Request Validation)
    ↓
Services (Business Logic)
    ↓
Models (Database Operations)
    ↓
Response (JSON/HTTP)
```

### 🏃 Background Jobs Flow

```
APScheduler
    ├── Gmail Sync Job (Every 6 Hours)
    │   ├── Credit Validation → Gmail Service
    │   ├── Email Fetching → Attachment Service
    │   └── Data Processing → LLM Service
    │
    ├── Token Refresh (Every 1 Hour)
    │   └── OAuth Token Management
    │
    └── Email Processing (Every 6 Hours)
        ├── Unprocessed Email Detection
        ├── AI Document Analysis
        └── Structured Data Extraction
```

## Quick Start

```bash
# Backend
pip install -r requirements.txt
cp .env.example .env  # Add your credentials

# Frontend
cd frontend && npm install

# Run with Docker
docker-compose up -d

# Or run separately
uvicorn app.main:app --reload  # Backend :8000
cd frontend && npm run dev      # Frontend :8080
```

## Features

- Manual expense tracking with categories
- Gmail OAuth integration for receipt imports
- AI-powered PDF/image processing (OpenAI)
- Credit-based subscription system (100 free credits on signup)
- S3 file storage
- Scheduled background jobs for email sync

## Tech Stack

**Backend:** FastAPI, PostgreSQL, SQLAlchemy, Alembic, APScheduler, JWT, Google OAuth, AWS S3, OpenAI  
**Frontend:** React 18, TypeScript, Vite, Redux Toolkit, React Query, Tailwind, Shadcn/ui

## Project Structure

```
app/
├── main.py              # FastAPI app + scheduler
├── controller/          # Request handlers
├── services/            # Business logic (Gmail, LLM, S3, DB, subscriptions)
├── models/              # SQLAlchemy models + Pydantic schemas
├── routes/              # API endpoints
├── middleware/          # Auth + request tracking
└── migrations/          # Alembic migrations

frontend/src/
├── components/          # UI components
├── pages/               # Route pages
├── lib/                 # API client
└── store/               # Redux state
```

## Environment Setup

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/fintrack

# Auth
JWT_SECRET=your-secret
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# AWS
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
S3_BUCKET_NAME=your-bucket

# LLM
OPENAI_API_KEY=your-openai-key

# URLs
FRONTEND_URL=http://localhost:8080
VITE_API_BASE_URL=http://localhost:8000/api
```

## Database

```bash
# Run migrations
cd app
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"
```

**Schema:** users, expenses, sources, emails, attachments, processed_email_data, subscriptions, plans, features, credit_history, integrations

## API Endpoints

### Auth
- `GET /api/login` - Google OAuth flow
- `GET /api/emails/oauth2callback` - OAuth callback

### Expenses
- `GET /api/expense` - List expenses
- `POST /api/expense` - Create expense
- `PUT /api/expense/{id}` - Update expense
- `DELETE /api/expense/{id}` - Delete expense

### Processing
- `POST /api/emails` - Trigger email sync (1 credit)
- `GET /api/payment/info` - Get imported transactions
- `POST /api/upload` - Upload PDF/image (2-3 credits)

### User
- `GET /api/user` - Profile
- `GET /api/user/settings` - Integrations + credits
- `PUT /api/user` - Update profile

## Background Jobs

- **Gmail Sync** - Every 6 hours
- **Token Refresh** - Every hour
- **Email Processing** - Every 6 hours

Jobs use APScheduler and run in the main FastAPI process via [app/main.py](app/main.py).

## Credit System

| Feature | Cost |
|---------|------|
| Gmail Sync | 1 credit |
| Email Processing | 1 credit |
| PDF Upload | 2 credits |
| LLM Processing | 3 credits |

New users get 100 credits (30-day trial). Check [`app/services/subscription_service.py`](app/services/subscription_service.py) for billing logic.

## File Upload

Supports PDF and images (JPG, PNG, WEBP). Files are processed via:
1. Upload to S3 ([`app/services/s3_service.py`](app/services/s3_service.py))
2. Text extraction ([`app/services/file_service.py`](app/services/file_service.py))
3. LLM analysis ([`app/services/llm/service.py`](app/services/llm/service.py))

See [`app/controller/controller.py`](app/controller/controller.py) `FileController.upload_file()` for implementation.

## Architecture

```
Request → Middleware (JWT) → Routes → Controller → Services → Database
                                                  ↓
                                              S3/LLM/Gmail
```

Background jobs run via APScheduler in [`app/services/cron_service.py`](app/services/cron_service.py).

## Development

- Frontend uses Vite proxy for API calls ([`frontend/vite.config.ts`](frontend/vite.config.ts))
- Backend handles CORS in [`app/main.py`](app/main.py)
- Errors use centralized handlers ([`app/utils/exception_handlers.py`](app/utils/exception_handlers.py))
- Database models use mixins for timestamps/soft deletes ([`app/models/models.py`](app/models/models.py))

## Deployment

```bash
# Production
docker-compose up -d

# Health check
curl http://localhost:8000/health
```

Configure SSL, monitoring, and backups for production use.

## License

MIT

