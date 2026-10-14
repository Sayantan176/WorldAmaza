import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import resend
from sqlalchemy.orm import Session
from app.config import settings
from app.models import Digest, User, Watch, Event, WatchMatch, EventArticle, Article

logger = logging.getLogger("worldamaze.digest")


def build_digest_email_html(user_email: str, period: str, date_str: str, watch_groups: List[dict]) -> str:
    """Builds clean, light-mode responsive email for daily/weekly digest."""
    content_html = ""
    for group in watch_groups:
        watch_title = group["watch_title"]
        events = group["events"]
        events_html = ""
        for ev in events:
            sources_html = "".join([
                f"""<a href="{s.get('url', '#')}" style="color: #2563eb; text-decoration: underline; margin-right: 12px; font-size: 12px;">{s.get('source_name', 'Source')}</a>"""
                for s in ev.get("sources", [])
            ])
            events_html += f"""
            <div style="margin-bottom: 20px; padding: 14px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px;">
                <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600; margin-bottom: 4px;">
                    {ev['importance'].upper()} • {ev['evidence_status'].replace('_', ' ').upper()}
                </div>
                <h3 style="font-size: 16px; margin: 0 0 8px 0; color: #0f172a;">{ev['headline']}</h3>
                <p style="font-size: 13px; color: #334155; line-height: 1.5; margin: 0 0 10px 0;">{ev['summary']}</p>
                <div>{sources_html}</div>
            </div>
            """

        content_html += f"""
        <div style="margin-bottom: 28px;">
            <h2 style="font-size: 15px; font-weight: 700; color: #1e293b; border-bottom: 1px solid #cbd5e1; padding-bottom: 6px; margin-bottom: 12px;">
                Watch: {watch_title}
            </h2>
            {events_html}
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #0f172a;">
        <div style="max-width: 640px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 32px;">
            <div style="border-bottom: 1px solid #e2e8f0; padding-bottom: 16px; margin-bottom: 24px;">
                <span style="font-weight: 700; font-size: 18px; color: #0f172a;">WorldAmaze</span>
                <span style="font-size: 13px; color: #64748b; margin-left: 8px;">{period.capitalize()} Intelligence Digest • {date_str}</span>
            </div>
            <p style="font-size: 14px; color: #475569; margin-bottom: 24px;">
                Here is your curated intelligence summary based on your active monitoring watches.
            </p>
            {content_html or "<p style='color: #64748b; font-style: italic;'>No developments detected for this period.</p>"}
            <div style="border-top: 1px solid #e2e8f0; padding-top: 20px; font-size: 12px; color: #94a3b8; text-align: center;">
                Delivered by WorldAmaze • Global Intelligence Monitoring Platform
            </div>
        </div>
    </body>
    </html>
    """


class DigestService:
    def __init__(self):
        if settings.RESEND_API_KEY:
            resend.api_key = settings.RESEND_API_KEY

    def compile_digest_preview(self, db: Session, user: User, period: str = "daily") -> Dict[str, Any]:
        """Compiles a digest preview for a user without saving to database."""
        now = datetime.now(timezone.utc)
        lookback_days = 7 if period == "weekly" else 1
        cutoff = now - timedelta(days=lookback_days)

        user_watches = db.query(Watch).filter(
            Watch.user_id == user.id,
            Watch.status == "active"
        ).all()

        watch_groups = []
        total_events = 0

        for watch in user_watches:
            matches = db.query(WatchMatch).filter(
                WatchMatch.watch_id == watch.id,
                WatchMatch.created_at >= cutoff
            ).all()

            if not matches:
                continue

            events_data = []
            for m in matches:
                event = db.query(Event).filter(Event.id == m.event_id).first()
                if not event:
                    continue

                # Fetch sources
                ea_links = db.query(EventArticle).filter(EventArticle.event_id == event.id).all()
                sources = []
                for link in ea_links:
                    art = db.query(Article).filter(Article.id == link.article_id).first()
                    if art:
                        sources.append({
                            "source_name": art.source_name,
                            "url": art.canonical_url,
                            "title": art.title
                        })

                events_data.append({
                    "id": event.id,
                    "headline": event.headline,
                    "summary": event.summary,
                    "what_changed": event.what_changed,
                    "importance": event.importance,
                    "evidence_status": event.evidence_status,
                    "match_rationale": m.match_rationale,
                    "sources": sources,
                    "created_at": event.first_detected_at.isoformat() if event.first_detected_at else None,
                })

            if events_data:
                total_events += len(events_data)
                watch_groups.append({
                    "watch_id": watch.id,
                    "watch_title": watch.title,
                    "events": events_data
                })

        return {
            "period": period,
            "date": now.strftime("%B %d, %Y"),
            "total_events": total_events,
            "watch_groups": watch_groups
        }

    def generate_and_deliver_digest(
        self,
        db: Session,
        user: User,
        period: str = "daily",
        force_send_email: bool = False
    ) -> Optional[Digest]:
        """
        Compiles the digest, records it in the database, and delivers email if configured.
        """
        preview = self.compile_digest_preview(db, user, period=period)
        if preview["total_events"] == 0 and not force_send_email:
            logger.info(f"No events found for {period} digest for user {user.email}. Skipping generation.")
            return None

        title = f"{period.capitalize()} Intelligence Digest — {preview['date']}"
        digest = Digest(
            user_id=user.id,
            title=title,
            period=period,
            event_count=preview["total_events"],
            content=json.dumps(preview),
            email_sent=False,
            email_status="pending" if (user.email_notifications_enabled and settings.EMAIL_ENABLED) else "skipped",
        )
        db.add(digest)
        db.commit()
        db.refresh(digest)

        if (user.email_notifications_enabled or force_send_email) and settings.EMAIL_ENABLED:
            try:
                html = build_digest_email_html(user.email, period, preview["date"], preview["watch_groups"])
                sender = settings.RESEND_FROM_EMAIL or "onboarding@resend.dev"
                params = {
                    "from": sender,
                    "to": [user.email],
                    "subject": f"[WorldAmaze] {title}",
                    "html": html,
                }
                logger.info(f"Dispatching Resend digest email to {user.email} from {sender}...")
                resp = resend.Emails.send(params)
                digest.email_sent = True
                digest.email_status = "delivered"
                digest.email_error = None
                db.commit()
                logger.info(f"Digest email sent to {user.email}: {resp}")
            except Exception as e:
                err_msg = str(e)
                logger.warning(f"Resend digest email failed for {user.email}: {err_msg}")
                digest.email_sent = False
                digest.email_status = "failed"
                digest.email_error = err_msg[:500]
                db.commit()

        return digest


digest_service = DigestService()
