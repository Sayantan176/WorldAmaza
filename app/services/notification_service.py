import logging
from typing import Optional, List
import resend
from sqlalchemy.orm import Session
from app.config import settings
from app.models import Notification, Event, Watch, User, Article

logger = logging.getLogger("worldamaze.notifications")


def build_alert_email_html(
    watch_title: str,
    headline: str,
    summary: str,
    what_changed: str,
    match_rationale: str,
    evidence_status: str,
    importance: str,
    sources: List[dict],
) -> str:
    """Builds a restrained, clean, light-mode email for an immediate alert."""
    sources_html = ""
    for s in sources:
        url = s.get("url", "#")
        name = s.get("source_name", "Source")
        title = s.get("title", "Read article")
        sources_html += f"""
        <li style="margin-bottom: 6px;">
            <a href="{url}" style="color: #2563eb; text-decoration: underline; font-size: 13px;">{name}: {title}</a>
        </li>
        """

    evidence_badge_color = "#16a34a" if evidence_status == "official_confirmed" else "#d97706"
    importance_badge_color = "#dc2626" if importance in ("critical", "high") else "#4b5563"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{headline}</title>
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #0f172a;">
        <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 32px;">
            
            <div style="border-bottom: 1px solid #e2e8f0; padding-bottom: 16px; margin-bottom: 24px;">
                <span style="font-weight: 700; font-size: 16px; letter-spacing: -0.02em; color: #0f172a;">WorldAmaze</span>
                <span style="font-size: 12px; color: #64748b; margin-left: 8px;">Intelligence Watch Alert</span>
            </div>

            <div style="margin-bottom: 12px;">
                <span style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b;">Watch: {watch_title}</span>
            </div>

            <h1 style="font-size: 20px; font-weight: 700; line-height: 1.3; color: #0f172a; margin: 0 0 16px 0;">
                {headline}
            </h1>

            <div style="margin-bottom: 20px;">
                <span style="display: inline-block; padding: 2px 8px; font-size: 11px; font-weight: 600; border-radius: 4px; background: #f1f5f9; color: {importance_badge_color}; margin-right: 6px;">
                    {importance.upper()} IMPORTANCE
                </span>
                <span style="display: inline-block; padding: 2px 8px; font-size: 11px; font-weight: 600; border-radius: 4px; background: #f1f5f9; color: {evidence_badge_color};">
                    {evidence_status.replace('_', ' ').upper()}
                </span>
            </div>

            <div style="background-color: #f8fafc; border-left: 3px solid #2563eb; padding: 12px 16px; margin-bottom: 20px;">
                <p style="margin: 0; font-size: 14px; line-height: 1.5; color: #334155;">
                    <strong>What changed:</strong> {what_changed or summary}
                </p>
            </div>

            <div style="margin-bottom: 24px;">
                <h3 style="font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; margin-bottom: 6px;">Executive Summary</h3>
                <p style="font-size: 14px; line-height: 1.6; color: #1e293b; margin: 0;">
                    {summary}
                </p>
            </div>

            <div style="margin-bottom: 24px;">
                <h3 style="font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; margin-bottom: 6px;">Why this matched your rules</h3>
                <p style="font-size: 13px; line-height: 1.5; color: #475569; margin: 0;">
                    {match_rationale}
                </p>
            </div>

            <div style="margin-bottom: 28px;">
                <h3 style="font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; margin-bottom: 8px;">Supporting Sources</h3>
                <ul style="padding-left: 20px; margin: 0; color: #475569;">
                    {sources_html or "<li>Verified source reports</li>"}
                </ul>
            </div>

            <div style="border-top: 1px solid #e2e8f0; padding-top: 20px; font-size: 12px; color: #94a3b8; text-align: center;">
                Delivered by WorldAmaze • You received this alert because you configured "{watch_title}".
            </div>
        </div>
    </body>
    </html>
    """


class NotificationService:
    def __init__(self):
        if settings.RESEND_API_KEY:
            resend.api_key = settings.RESEND_API_KEY

    def create_notification(
        self,
        db: Session,
        user: User,
        watch: Watch,
        event: Event,
        match_rationale: str,
        sources: List[dict],
        send_email: bool = True
    ) -> Notification:
        """
        Creates an in-app notification idempotently, and delivers an email
        via Resend if requested and user has email notifications enabled.
        """
        # Idempotency check: don't create duplicate notification for same (user, watch, event)
        existing = db.query(Notification).filter(
            Notification.user_id == user.id,
            Notification.watch_id == watch.id,
            Notification.event_id == event.id,
        ).first()

        if existing:
            return existing

        notification = Notification(
            user_id=user.id,
            watch_id=watch.id,
            event_id=event.id,
            is_read=False,
            delivery_channel="both" if (send_email and user.email_notifications_enabled) else "in_app",
            email_sent=False,
            email_status="pending" if (send_email and user.email_notifications_enabled) else "skipped",
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)

        # Attempt email sending if enabled
        if send_email and user.email_notifications_enabled and settings.EMAIL_ENABLED:
            self._deliver_email(db, notification, user, watch, event, match_rationale, sources)

        return notification

    def _deliver_email(
        self,
        db: Session,
        notification: Notification,
        user: User,
        watch: Watch,
        event: Event,
        match_rationale: str,
        sources: List[dict],
    ):
        try:
            html = build_alert_email_html(
                watch_title=watch.title,
                headline=event.headline,
                summary=event.summary,
                what_changed=event.what_changed,
                match_rationale=match_rationale,
                evidence_status=event.evidence_status,
                importance=event.importance,
                sources=sources,
            )
            sender = settings.RESEND_FROM_EMAIL or "onboarding@resend.dev"
            params = {
                "from": sender,
                "to": [user.email],
                "subject": f"[WorldAmaze Alert] {event.headline}",
                "html": html,
            }
            logger.info(f"Dispatching Resend alert email to {user.email} from {sender}...")
            resp = resend.Emails.send(params)
            
            notification.email_sent = True
            notification.email_status = "delivered"
            notification.email_error = None
            db.commit()
            logger.info(f"Email delivered successfully to {user.email}: {resp}")

        except Exception as e:
            err_msg = str(e)
            logger.warning(f"Resend email delivery notice for {user.email}: {err_msg}")
            notification.email_sent = False
            notification.email_status = "failed"
            notification.email_error = err_msg[:500]
            db.commit()


notification_service = NotificationService()
