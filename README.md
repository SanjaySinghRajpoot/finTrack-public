# FinTrack

A modern full-stack financial tracking application that combines automated email processing with manual expense management. Built with FastAPI backend and React frontend, featuring Gmail integration for automatic transaction processing, intelligent document parsing with OCR support, document staging pipeline, custom schema management, and a credit-based subscription system.

## Product Images
<img width="2544" height="1272" alt="Screenshot 2025-11-16 at 6 36 42 PM" src="https://github.com/user-attachments/assets/60ae443b-0b86-47a2-bda2-a9c46321114b" />

<img width="2557" height="1272" alt="Screenshot 2025-11-16 at 6 36 51 PM" src="https://github.com/user-attachments/assets/eae47f6e-9dc0-468e-8d1c-7ed5ff297f56" />

<img width="2557" height="1272" alt="Screenshot 2025-11-16 at 6 36 58 PM" src="https://github.com/user-attachments/assets/8a730d14-4549-4c63-bcfa-bbeedca75297" />

<img width="2557" height="1272" alt="Screenshot 2025-11-16 at 6 37 06 PM" src="https://github.com/user-attachments/assets/e4e1a393-ce05-45fe-87c5-87dabba70a9b" />


## Features

-   **Manual Expense Tracking** — Effortlessly add, edit, and categorize your expenses with a user-friendly interface. Gain full control over your financial records by manually inputting transactions.
-   **Gmail Integration** — Securely connect your Gmail account via OAuth to automatically import receipts and transaction details directly into FinTrack, reducing manual data entry.
-   **AI Document Processing** — Leverage OpenAI's advanced AI capabilities to intelligently extract key data from uploaded PDF documents and image files, such as invoices and receipts, for streamlined expense recording.
-   **OCR Support** — Built-in OCR (Optical Character Recognition) service for processing scanned documents and images, extracting text from non-digital documents.
-   **Document Staging Pipeline** — Asynchronous document processing queue with retry logic, status tracking, and batch processing capabilities for handling multiple documents efficiently.
-   **Custom Schema Management** — Define and manage custom fields for your documents beyond the default schema, allowing for personalized data extraction and organization.
-   **Modular Integration System** — Extensible integration framework supporting multiple providers (Gmail, Outlook, etc.) with a plugin-based architecture for easy addition of new integrations.
-   **Credit System** — Start your financial tracking journey with 100 free credits upon signup, which can be used for AI document processing and other premium features.
-   **Background Jobs** — Automated scheduled tasks ensure your financial data is always up-to-date, including regular email synchronization for new receipts and background processing of documents.
-   **Asynchronous Invoice Processing** — Upload invoices and receipts for background processing, allowing you to continue using the application without interruption while AI extracts data.
-   **Direct S3 Upload** — Generate presigned URLs for direct file uploads to S3, with duplicate detection via file hashing.

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Backend | FastAPI, PostgreSQL, SQLAlchemy, Alembic, APScheduler |
| Frontend | React 18, TypeScript, Vite, Redux Toolkit, Tailwind, Shadcn/ui |
| Integrations | Google OAuth, AWS S3, OpenAI |
| Processing | OCR (Tesseract/Cloud Vision), LLM (OpenAI), Document Pipeline |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (or Bun)
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
npm install  # or: bun install
npm run dev  # or: bun run dev
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
├── main.py                     # FastAPI entry + scheduler + lifespan management
├── controller/                 # Request handlers (separated by domain)
│   ├── auth_controller.py      # Authentication & OAuth
│   ├── user_controller.py      # User management
│   ├── expense_controller.py   # Expense CRUD operations
│   ├── file_controller.py      # File uploads & S3 operations
│   ├── email_controller.py     # Email sync triggers
│   ├── integration_controller.py  # Integration linking/delinking
│   ├── processed_data_controller.py  # Processed documents & staging
│   └── custom_schema_controller.py   # Custom schema management
├── services/                   # Business logic layer
│   ├── db_service.py           # Database operations & queries
│   ├── user_service.py         # User-related operations
│   ├── gmail_service.py        # Gmail API integration
│   ├── subscription_service.py # Credit & billing logic
│   ├── s3_service.py           # AWS S3 file storage
│   ├── jwt_service.py          # JWT token handling
│   ├── token_service.py        # OAuth token refresh
│   ├── file_service.py         # File processing utilities
│   ├── file_processor_service.py  # PDF text extraction
│   ├── document_processor_service.py  # Unified document processing
│   ├── document_staging_service.py    # Staging status management
│   ├── custom_schema_service.py       # Custom field management
│   ├── cron_service.py         # Scheduled jobs (base classes + implementations)
│   ├── email_attachment_service.py
│   ├── feature_service.py      # Feature management
│   ├── initial_setup_service.py  # Database initialization
│   ├── integration/            # Modular integration system
│   │   ├── base_integration_service.py  # Base integration interface
│   │   ├── gmail_integration.py         # Gmail-specific logic
│   │   ├── registry.py         # Integration registry
│   │   ├── handlers.py         # Request handlers
│   │   ├── validators.py       # Input validation
│   │   ├── query_service.py    # Integration queries
│   │   └── creation_service.py # Integration creation
│   ├── llm/                    # LLM processing
│   │   ├── service.py          # OpenAI document analysis
│   │   ├── base.py             # Base LLM interface
│   │   ├── models.py           # LLM data models
│   │   └── processors/         # Document-specific processors
│   └── ocr/                    # OCR processing
│       ├── service.py          # OCR orchestration
│       └── models.py           # OCR data models
├── models/
│   ├── models.py               # SQLAlchemy ORM models
│   ├── scheme.py               # Pydantic request/response schemas
│   ├── integration_schemas.py  # Integration-specific schemas
│   └── event_handlers.py       # Database event handlers
├── repositories/               # Data access layer
│   ├── custom_schema_repository.py
│   ├── document_repository.py
│   └── ... (other repositories)
├── routes/
│   └── routes.py               # API endpoint definitions
├── middleware/
│   ├── auth_middleware.py      # JWT authentication
│   └── request_id_middleware.py  # Request tracking
├── utils/
│   ├── exception_handlers.py   # Centralized error handling
│   ├── exceptions.py           # Custom exception classes
│   └── oauth.py                # OAuth utilities
├── constants/
│   └── integration_constants.py  # Integration configuration
├── core/                       # Core utilities
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
├── tailwind.config.ts
└── bun.lockb                   # Bun package manager
```

## API Endpoints

### Authentication
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/login` | GET | Google OAuth login |
| `/api/emails/oauth2callback` | GET | OAuth callback |

### User Management
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/user` | GET | Get user profile |
| `/api/user` | PUT | Update profile |
| `/api/user/settings` | GET | Get integrations & credits |

### Expense Management
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/expense` | GET | List expenses (paginated) |
| `/api/expense` | POST | Create expense |
| `/api/expense/{id}` | GET | Get single expense |
| `/api/expense/{id}` | PUT | Update expense |
| `/api/expense/{id}` | DELETE | Delete expense |

### Email & Integration
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/emails` | POST | Trigger email sync |
| `/api/integration/{slug}/link` | GET | Initiate integration linking |
| `/api/integration/{slug}/callback` | GET | OAuth callback handler |
| `/api/integration/{slug}/delink` | DELETE | Remove integration |

### File & Document Management
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload` | POST | Upload PDF/image (legacy) |
| `/api/files/presigned-urls` | POST | Get S3 presigned URLs for upload |
| `/api/files/metadata` | POST | Process uploaded file metadata |
| `/api/attachment/view` | GET | Get signed URL for viewing |

### Document Processing
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/processed-expense/info` | GET | List processed documents (paginated) |
| `/api/staging-documents` | GET | Get staging queue status |

### Custom Schema
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/schema` | GET | Get full document schema |
| `/api/schema/custom` | POST | Create custom schema fields |
| `/api/schema/custom` | PUT | Update custom schema |
| `/api/schema/custom` | DELETE | Delete custom schema |

## Database Schema

**Core Tables:** `users`, `expenses`, `sources`, `emails`, `attachments`, `processed_email_data`, `manual_uploads`, `document_staging`

**Subscription:** `subscriptions`, `plans`, `features`, `credit_history`

**Integrations:** `integrations`, `custom_schemas`

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
| OCR Processing | 2 |

New users receive 100 credits with a 30-day trial.

## Architecture

### Request Flow
```
Request → RequestIDMiddleware → Auth (JWT) → Routes → Controller → Services → Repository → Database
                                                           ↓
                                                    S3 / OpenAI / Gmail / OCR
```

### Document Processing Pipeline

```
File Upload → S3 Storage → Document Staging (Queue)
                                    ↓
                         Cron Job Processor (5 min intervals)
                                    ↓
              ┌─────────────────────┴─────────────────────┐
              ↓                                           ↓
     Email Documents                            Manual Uploads
              ↓                                           ↓
    Has Attachment?                              OCR (if image)
     ↓           ↓                                        ↓
   Yes          No                               Text Extraction
     ↓           ↓                                        ↓
  OCR/PDF    HTML Content                          LLM Processing
     ↓           ↓                                        ↓
     └───────────┴─────────────────────────────────────→ ProcessedEmailData
```

### Background Jobs (APScheduler)

| Job | Frequency | Description |
|-----|-----------|-------------|
| `Every24HoursCronJob` | Every 6 hours | Gmail sync for all connected users |
| `Every1HourTokenRefreshCronJob` | Every 1 hour | Refresh expired OAuth tokens |
| `IsEmailProcessedCheckCRON` | Every 6 hours | Process unprocessed emails |
| `DocumentStagingProcessorCron` | Every 6 seconds* | Process pending documents from staging queue |

*Configurable interval - processes up to 10 documents per run

### Key Features

#### 1. **Document Staging System**
- Asynchronous processing queue for all document types
- Retry logic with configurable max attempts
- Status tracking (PENDING, IN_PROGRESS, COMPLETED, FAILED)
- Support for email attachments, manual uploads, and HTML content

#### 2. **Modular Integration Framework**
- Registry-based integration system
- Easy addition of new providers (Outlook, Dropbox, etc.)
- Unified OAuth callback handling
- Provider-specific configuration management

#### 3. **Custom Schema Management**
- Define custom fields beyond default schema
- User-specific field configurations
- Type validation (string, number, date, boolean, array)
- Merge with default schema for comprehensive data extraction

#### 4. **OCR Processing**
- Support for scanned documents and images
- Automatic text extraction from non-digital documents
- Integration with document processing pipeline
- Fallback options for failed OCR attempts

#### 5. **Enhanced Error Handling**
- Centralized exception handling
- Custom exception classes
- Request ID tracking for debugging
- Detailed error logging

## Development

### Running Tests
```bash
# Backend tests
pytest

# Frontend tests
cd frontend && npm test
```

### Code Structure Principles

- **Controller Layer**: HTTP request/response handling only
- **Service Layer**: Business logic and orchestration
- **Repository Layer**: Database queries and data access
- **Middleware**: Cross-cutting concerns (auth, logging, request tracking)

## License

MIT