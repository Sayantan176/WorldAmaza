import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from app.config import settings
from app.jobs.monitoring_job import run_all_active_watches_monitoring
from app.jobs.digest_job import run_scheduled_digests

logger = logging.getLogger("worldamaze.scheduler")

scheduler = BackgroundScheduler()


def start_scheduler():
    """Initializes and starts the APScheduler background worker."""
    if not settings.SCHEDULER_ENABLED:
        logger.info("Scheduler is disabled by configuration.")
        return

    if scheduler.running:
        logger.info("Scheduler is already running.")
        return

    # Add active watch monitoring job
    polling_mins = max(5, settings.DEFAULT_POLLING_INTERVAL_MINUTES)
    scheduler.add_job(
        run_all_active_watches_monitoring,
        trigger=IntervalTrigger(minutes=polling_mins),
        id="monitoring_pipeline",
        name="Scheduled Active Watches Monitoring",
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )

    # Add digest generation job running every hour to check user local timezones
    scheduler.add_job(
        run_scheduled_digests,
        trigger=CronTrigger(minute=0),
        id="digest_pipeline",
        name="Hourly Digest Processor",
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )

    scheduler.start()
    logger.info(f"APScheduler started successfully. Watch polling every {polling_mins}m, digest check hourly.")


def stop_scheduler():
    """Gracefully shuts down the background scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped.")
