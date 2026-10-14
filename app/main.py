import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.jobs.scheduler import start_scheduler, stop_scheduler
from app.routers import (
    auth,
    dashboard,
    watches,
    notifications,
    digests,
    history,
    settings as settings_router,
    api,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("worldamaze")

# Ensure database tables exist immediately on module import (critical for WSGI servers)
try:
    init_db()
except Exception as e:
    logger.warning(f"Notice during startup init_db: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence
    logger.info("Starting WorldAmaze Intelligence Platform...")
    init_db()
    start_scheduler()
    logger.info("WorldAmaze initialization complete.")
    yield
    # Shutdown sequence
    logger.info("Shutting down WorldAmaze...")
    stop_scheduler()
    logger.info("WorldAmaze shutdown complete.")


app = FastAPI(
    title="WorldAmaze",
    description="Personal Global Intelligence Monitoring Platform",
    version="1.0.0",
    lifespan=lifespan
)

# Security and CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files using absolute directory path
APP_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(APP_DIR, "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Health Check Endpoint
@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "WorldAmaze",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "engine": "active"
    }


# Include Routers
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(watches.router)
app.include_router(notifications.router)
app.include_router(digests.router)
app.include_router(history.router)
app.include_router(settings_router.router)
app.include_router(api.router)


# Global Safe Error Handlers
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {type(exc).__name__} {exc}")
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "An internal error occurred while processing your intelligence request."}
        )
    # For HTML requests, let Starlette render or return a clean error
    from fastapi.responses import HTMLResponse
    return HTMLResponse(
        """
        <!DOCTYPE html>
        <html>
        <head><title>System Error — WorldAmaze</title><link rel="stylesheet" href="/static/css/main.css"></head>
        <body class="p-12 bg-slate-50 text-slate-800 font-sans">
            <div class="max-w-md mx-auto bg-white p-8 border border-slate-200 rounded-lg shadow-sm text-center">
                <h2 class="text-xl font-bold text-slate-900 mb-2">Notice</h2>
                <p class="text-sm text-slate-600 mb-6">A temporary system error occurred. Details have been logged safely.</p>
                <a href="/dashboard" class="px-4 py-2 bg-slate-900 text-white text-xs font-semibold rounded hover:bg-slate-800">Return to Overview</a>
            </div>
        </body>
        </html>
        """,
        status_code=500
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
