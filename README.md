# FinTrack

A modern full-stack financial tracking application that combines automated email processing with manual expense management. Built with FastAPI backend and React frontend, featuring Gmail integration for automatic transaction processing, intelligent document parsing, and a credit-based subscription system.

## 🏗️ Backend Code Structure

```
app/
├── main.py                    # FastAPI application entry point with lifespan management
├── db_config.py              # Database configuration and session management
├── alembic.ini               # Alembic configuration for database migrations
│
├── controller/               # Request handling and business logic coordination
│   └── controller.py         # Main controller with endpoint logic
│
├── middleware/               # Custom middleware for request processing
│   ├── auth_middleware.py    # JWT authentication middleware
│   └── request_id_middleware.py  # Request ID tracking for logging
│
├── models/                   # SQLAlchemy database models
│   └── models.py            # Complete database schema definitions
│       ├── User, UserToken  # User management and authentication
│       ├── Source, Email    # Email processing and source tracking
│       ├── Attachment       # File storage and metadata
│       ├── ProcessedEmailData, ProcessedItem  # Extracted financial data
│       ├── Expense          # Manual expense management
│       ├── Plan, Feature, Subscription  # Subscription and billing
│       ├── Integration*     # Integration framework tables
│       └── CreditHistory    # Credit usage tracking
│
├── routes/                   # API endpoint definitions
│   └── routes.py            # All REST API routes and FastAPI router
│
├── services/                 # Business logic and external integrations
│   ├── subscription_service.py   # Credit management and billing logic
│   ├── gmail_service.py          # Gmail API integration and email processing
│   ├── user_service.py           # User management and profile operations
│   ├── db_service.py             # Database operations and queries
│   ├── integration_service.py    # Integration framework management
│   ├── email_attachment_service.py  # Email attachment processing
│   ├── llm_service.py            # AI/LLM document processing
│   ├── s3_service.py             # AWS S3 file storage operations
│   ├── file_service.py           # File handling and processing
│   ├── jwt_service.py            # JWT token management
│   ├── token_service.py          # OAuth token operations
│   └── cron_service.py           # Scheduled background jobs
│       ├── Every24HoursCronJob   # Gmail sync automation
│       ├── Every1HourTokenRefreshCronJob  # Token refresh
│       └── IsEmailProcessedCheckCRON      # Email processing check
│
├── utils/                    # Utility functions and helpers
│   ├── exception_handlers.py     # Centralized error handling
│   ├── exceptions.py             # Custom exception definitions
│   ├── oauth_utils.py            # OAuth flow utilities
│   └── utils.py                  # General utility functions
│
└── migrations/               # Database migration files (Alembic)
    ├── env.py               # Alembic environment configuration
    ├── script.py.mako       # Migration template
    └── versions/            # Individual migration files

Root Level Files:
├── docker-compose.yml        # Multi-container Docker setup
├── Dockerfile               # Backend container definition
├── nginx.conf               # Nginx reverse proxy configuration
├── credentials.json         # Google OAuth credentials
└── requirements.txt         # Python dependencies
```

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

## 🚀 Features

### Core Functionality
- **Expense Management**: Create, read, update, and delete personal expenses
- **Gmail Integration**: Automatic processing of financial emails (invoices, bills, receipts)
- **Document Processing**: AI-powered extraction of financial data from PDF attachments
- **Import System**: Review and import automatically processed transactions
- **User Dashboard**: Analytics and insights with expense categorization
- **Real-time Sync**: Scheduled background jobs for email synchronization
- **Credit-Based Billing**: Subscription plans with credit allocation for feature usage
- **Multi-Integration Support**: Extensible integration framework for Gmail, WhatsApp, and more

### Subscription & Credit System
- **Flexible Plans**: Trial, active, and custom subscription plans with credit allocation
- **Feature-Based Billing**: Different features consume different amounts of credits
- **Credit Tracking**: Real-time credit balance monitoring and usage history
- **Auto Credit Validation**: Automatic credit validation before feature execution
- **Subscription Management**: Trial periods, renewals, and plan upgrades

### Technical Features
- **JWT Authentication**: Secure user authentication with Google OAuth2
- **RESTful API**: Well-structured API endpoints with proper validation
- **Database Management**: PostgreSQL with Alembic migrations
- **File Storage**: AWS S3 integration for document storage
- **Background Tasks**: APScheduler for automated email processing and token refresh
- **Credit Management**: Comprehensive subscription and billing system
- **Integration Framework**: Modular integration system with status tracking
- **Responsive UI**: Modern React frontend with TypeScript
- **State Management**: Redux Toolkit for client-side state
- **Docker Support**: Containerized deployment

## 🛠 Tech Stack

### Backend
- **FastAPI** - High-performance Python web framework
- **PostgreSQL** - Primary database
- **SQLAlchemy** - ORM and database toolkit
- **Alembic** - Database migration tool
- **APScheduler** - Background job scheduling
- **JWT** - Authentication tokens
- **Google APIs** - Gmail integration and OAuth
- **AWS S3** - File storage
- **LLM Integration** - Document processing and data extraction

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Redux Toolkit** - State management
- **React Query** - Server state management
- **React Router** - Client-side routing
- **Tailwind CSS** - Styling framework
- **Shadcn/ui** - UI component library
- **Recharts** - Data visualization

## 📦 Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 13+
- Docker & Docker Compose (optional)
- AWS Account (for S3 storage)
- Google Cloud Project (for Gmail API)

### Environment Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd finTrack-public
   ```

2. **Backend Setup**
   ```bash
   # Install Python dependencies
   pip install -r requirements.txt
   
   # Set up environment variables
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   ```

4. **Google API Configuration**
   - Create a project in Google Cloud Console
   - Enable Gmail API and Google+ API
   - Create OAuth2 credentials
   - Download `credentials.json` to project root

### Database Setup

#### Using Docker (Recommended)
```bash
docker-compose up db -d
```

#### Manual Setup
```bash
# Create PostgreSQL database
createdb fintrack

# Run migrations
cd app
alembic upgrade head
```

### Running the Application

#### Development Mode
```bash
# Terminal 1: Start backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start frontend
cd frontend
npm run dev
```

#### Using Docker
```bash
docker-compose up -d
```

The application will be available at:
- Frontend: http://localhost:8080
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## 🔌 API Endpoints

### Authentication
- `GET /api/login` - Initiate Google OAuth flow
- `GET /api/emails/oauth2callback` - OAuth callback handler

### User Management
- `GET /api/user` - Get user profile
- `GET /api/user/settings` - Get user integration settings
- `GET /api/user/subscription` - Get user subscription details and credit balance

### Subscription Management
- `POST /api/subscription/create` - Create starter subscription for new users
- `GET /api/subscription/features` - Get available features and credit costs
- `GET /api/subscription/usage` - Get credit usage history and statistics
- `POST /api/subscription/validate` - Validate credits for specific feature usage

### Expense Management
- `POST /api/expense` - Create new expense
- `GET /api/expense` - List user expenses (paginated)
- `GET /api/expense/{id}` - Get specific expense
- `PUT /api/expense/{id}` - Update expense
- `DELETE /api/expense/{id}` - Delete expense

### Email & Document Processing
- `POST /api/emails` - Trigger email processing (consumes credits)
- `GET /api/payment/info` - Get processed email data (importable transactions)

### Integration Management
- `GET /api/integrations` - List available integrations
- `POST /api/integrations/{type}/connect` - Connect new integration
- `GET /api/integrations/status` - Get user's integration status
- `PUT /api/integrations/{id}/sync` - Trigger manual sync

### File Management
- `GET /api/attachment/view` - Get signed URL for PDF viewing
- `POST /api/upload-pdf` - Upload PDF to S3

### System
- `GET /` - API status
- `GET /health` - Health check with scheduler status and active jobs

## 🗃 Database Schema

### Core Tables
- **users** - User profiles and authentication
- **expenses** - Manual expense entries
- **sources** - Source tracking for data lineage
- **emails** - Processed Gmail messages
- **processed_email_data** - Extracted financial data from emails
- **processed_items** - Individual line items from invoices
- **attachments** - File metadata and S3 references

### Subscription & Billing Tables
- **plans** - Available subscription plans with credit allocation
- **features** - System features with credit costs
- **plan_features** - Junction table for plan-feature relationships
- **subscriptions** - User subscriptions with credit tracking
- **credit_history** - Transaction log for credit usage

### Integration Tables
- **integrations** - Master table for available integrations
- **integration_status** - User-specific integration status and sync tracking
- **integration_features** - Junction table for integration-feature relationships
- **email_config** - Gmail integration configuration
- **whatsapp_config** - WhatsApp integration configuration (future)
- **user_tokens** - OAuth tokens for various providers

## 🔄 Database Migrations

Navigate to the `/app` directory:

```bash
# Create new migration
alembic revision --autogenerate -m "migration description"

# Apply migrations
alembic upgrade head

# Check migration status
alembic current
```

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/fintrack

# JWT
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRY_MINUTES=60

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# AWS S3
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
S3_BUCKET_NAME=your-s3-bucket
AWS_REGION=us-east-1

# LLM Service (if using OpenAI for document processing)
OPENAI_API_KEY=your-openai-api-key
```

## 🔄 Background Jobs

The application runs scheduled cron jobs using APScheduler:

### Every 6 Hours - Gmail Sync Job
- **Purpose**: Fetches new emails from connected Gmail accounts
- **Credit Validation**: Validates user credits before processing
- **Features**: 
  - Credit-based processing (1 credit per Gmail sync operation)
  - Automatic email content extraction
  - PDF attachment processing
  - Batch processing for multiple users
  - Error handling and logging

### Every 1 Hour - Token Refresh Job
- **Purpose**: Refreshes expired OAuth tokens
- **Features**:
  - Automatic token renewal for Google OAuth
  - Prevents integration disconnection
  - Handles token expiration gracefully

### Every 6 Hours - Email Processing Job
- **Purpose**: Processes unprocessed emails and extracts financial data
- **Features**:
  - LLM-powered document analysis
  - Attachment text extraction
  - Structured data extraction for invoices and bills
  - Item-level detail extraction

## 💳 Subscription System

### Credit-Based Billing
The application uses a credit-based system where different features consume different amounts of credits:

- **Gmail Sync**: 1 credit per sync operation
- **Email Processing**: 1 credit per email processed
- **PDF Extraction**: 2 credits per PDF processed
- **LLM Processing**: 3 credits per AI analysis

### Subscription Plans
- **Starter Plan**: 100 credits, 30-day trial
- **Custom Plans**: Configurable credit allocation and pricing
- **Auto-renewal**: Configurable subscription renewal

### Credit Management
- Real-time credit balance tracking
- Usage history and analytics
- Credit validation before feature execution
- Automatic credit deduction after successful operations

## 🔗 Integration Framework

### Supported Integrations
- **Gmail**: Full email sync and processing with OAuth2
- **WhatsApp** (Coming Soon): Message and media processing
- **Google Drive** (Planned): Document sync and processing

### Integration Features
- **Status Tracking**: Real-time integration health monitoring
- **Sync Management**: Configurable sync intervals and scheduling
- **Error Handling**: Comprehensive error logging and recovery
- **Configuration Management**: Per-integration settings and credentials

## 🚀 Deployment

### Docker Deployment
```bash
# Build and run all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production Considerations
- Set up proper SSL certificates
- Configure environment-specific variables
- Set up monitoring and logging
- Configure backup strategies for PostgreSQL
- Set up CDN for static assets
- Monitor credit usage and subscription renewals
- Set up alerts for integration failures

## 📊 Features in Detail

### Automated Email Processing
- Connects to Gmail via OAuth2
- Filters emails for financial keywords
- Downloads and processes PDF attachments
- Extracts structured data using LLM services
- Stores processed data for user review
- Credit-based processing with validation

### Subscription Management
- Trial subscriptions for new users
- Credit allocation and tracking
- Feature-based billing
- Usage analytics and reporting
- Flexible plan configuration

### Integration Management
- Modular integration framework
- Status monitoring and health checks
- Configurable sync schedules
- Error handling and recovery
- Multi-provider support

### Document Intelligence
- PDF text extraction with credit tracking
- LLM-powered financial data extraction
- Support for invoices, bills, receipts, and tax documents
- Item-level detail extraction for invoices
- Structured data output with validation

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.