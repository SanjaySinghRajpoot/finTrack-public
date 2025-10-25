# FinTrack

A modern full-stack financial tracking application that combines automated email processing with manual expense management. Built with FastAPI backend and React frontend, featuring Gmail integration for automatic transaction processing and intelligent document parsing.

## 🚀 Features

### Core Functionality
- **Expense Management**: Create, read, update, and delete personal expenses
- **Gmail Integration**: Automatic processing of financial emails (invoices, bills, receipts)
- **Document Processing**: AI-powered extraction of financial data from PDF attachments
- **Import System**: Review and import automatically processed transactions
- **User Dashboard**: Analytics and insights with expense categorization
- **Real-time Sync**: Scheduled background jobs for email synchronization

### Technical Features
- **JWT Authentication**: Secure user authentication with Google OAuth2
- **RESTful API**: Well-structured API endpoints with proper validation
- **Database Management**: PostgreSQL with Alembic migrations
- **File Storage**: AWS S3 integration for document storage
- **Background Tasks**: APScheduler for automated email processing
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

### Expense Management
- `POST /api/expense` - Create new expense
- `GET /api/expense` - List user expenses (paginated)
- `GET /api/expense/{id}` - Get specific expense
- `PUT /api/expense/{id}` - Update expense
- `DELETE /api/expense/{id}` - Delete expense

### Email & Document Processing
- `POST /api/emails` - Trigger email processing
- `GET /api/payment/info` - Get processed email data (importable transactions)

### File Management
- `GET /api/attachment/view` - Get signed URL for PDF viewing
- `POST /api/upload-pdf` - Upload PDF to S3

### System
- `GET /` - API status
- `GET /health` - Health check with scheduler status

## 🗃 Database Schema

### Key Tables
- **users** - User profiles and authentication
- **expenses** - Manual expense entries
- **emails** - Processed Gmail messages
- **processed_email_data** - Extracted financial data from emails
- **attachments** - File metadata and S3 references
- **integration_status** - OAuth token management

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

The application runs scheduled tasks for:
- **Email Synchronization**: Fetches new emails every 24 hours
- **Token Refresh**: Refreshes OAuth tokens every hour
- **Document Processing**: Processes attachments and extracts financial data

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

## 📊 Features in Detail

### Automated Email Processing
- Connects to Gmail via OAuth2
- Filters emails for financial keywords
- Downloads and processes PDF attachments
- Extracts structured data using LLM services
- Stores processed data for user review

### Expense Categories
- Predefined categories with icons and colors
- Custom categorization support
- Analytics and reporting by category

### Document Intelligence
- PDF text extraction
- LLM-powered financial data extraction
- Support for invoices, bills, receipts, and tax documents
- Structured data output with validation

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.