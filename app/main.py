import logging
from contextlib import asynccontextmanager
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db_config import engine, SessionLocal
from app.models import models
from app.routes.routes import router
from app.services.cron_service import Every24HoursCronJob, Every1HourTokenRefreshCronJob, IsEmailProcessedCheckCRON, DocumentStagingProcessorCron
from app.services.initial_setup_service import run_initial_setup
from app.utils.exception_handlers import register_exception_handlers
from app.middleware.request_id_middleware import RequestIDMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Initialize scheduler
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        """Lifespan context manager for startup and shutdown events"""
        # Startup: Run initial setup
        logger.info("Running initial data setup...")
        try:
            run_initial_setup()
        except Exception as setup_error:
            logger.warning(f"Initial setup encountered an issue: {setup_error}")
            # Continue running even if setup fails (data might already exist)
        
        # Startup: Initialize and start scheduler
        logger.info("Starting scheduler...")

        # Register all cron jobs
        Every24HoursCronJob(scheduler).register()
        Every1HourTokenRefreshCronJob(scheduler).register()
        IsEmailProcessedCheckCRON(scheduler).register()
        DocumentStagingProcessorCron(scheduler).register()
        # Add more cron jobs here as needed

        scheduler.start()
        logger.info("Scheduler started successfully!")

        yield

        # Shutdown: Stop scheduler
        logger.info("Stopping scheduler...")
        scheduler.shutdown()
        logger.info("Scheduler stopped!")
    except Exception as e:
        logger.error(f"Error in lifespan: {str(e)}")
        raise e


# Create FastAPI app
app = FastAPI(title="FinTrack Running", lifespan=lifespan)

# Add Request ID middleware (should be added before other middlewares)
app.add_middleware(RequestIDMiddleware)

# Configure CORS
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register centralized exception handlers
register_exception_handlers(app)

# Include routers
app.include_router(router, prefix="/api", tags=["api"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "FinTrack API is running",
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "scheduler": "running" if scheduler.running else "stopped",
        "active_jobs": [job.id for job in scheduler.get_jobs()]
    }