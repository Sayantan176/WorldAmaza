import logging
from datetime import datetime, timezone
from app.database import get_db_context
from app.models import User
from app.services.digest_service import digest_service

logger = logging.getLogger("worldamaze.digest_job")


def run_scheduled_digests():
    """
    Checks all users configured for daily digests and generates
    digests for active users.
    """
    logger.info("Starting scheduled digests check...")
    with get_db_context() as db:
        users = db.query(User).filter(
            User.digest_frequency != "none",
            User.email_notifications_enabled == True
        ).all()

        for user in users:
            try:
                digest = digest_service.generate_and_deliver_digest(
                    db=db,
                    user=user,
                    period=user.digest_frequency or "daily",
                    force_send_email=False
                )
                if digest:
                    logger.info(f"Generated {user.digest_frequency} digest for user {user.email}")
            except Exception as e:
                logger.error(f"Error generating digest for {user.email}: {e}")
