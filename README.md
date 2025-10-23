# FinTrack

A FastAPI-based financial tracking application with automated email processing and scheduled tasks.

## Features

- RESTful API for financial data management
- Gmail integration for automatic transaction processing
- Scheduled cron jobs for data synchronization
- JWT authentication
- PostgreSQL database with Alembic migrations
- Dockerized deployment

## Installation

### Prerequisites
- Python 3.11+
- PostgreSQL
- Docker & Docker Compose (optional)

### Local Development

1. **Clone and setup**
   ```bash
   git clone <repository-url>
   cd fintrack
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Database setup**
   ```bash
   docker-compose up db -d
   ```

4. **Run migrations**
   ```bash
   cd app
   alembic upgrade head
   ```

5. **Start the application**
   ```bash
   uvicorn app.main:app --reload
   ```

### Docker Deployment

```bash
docker-compose up -d
```

## API Endpoints

- **Health Check**: `GET /health`
- **API Routes**: `GET /api/*`

## Database Migrations

Navigate to `/app` directory:
```bash
alembic revision --autogenerate -m "migration message"
alembic upgrade head
```

## Configuration

Set up `credentials.json` for Gmail API integration and configure environment variables for database connection.
