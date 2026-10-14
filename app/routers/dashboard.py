from fastapi import APIRouter, Request, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user, get_current_user_optional
from app.models import User, Watch, Notification, Event

router = APIRouter(tags=["Dashboard"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def index_page(request: Request, user=Depends(get_current_user_optional)):
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request=request, name="landing.html", context={
        "current_user": None,
        "active_page": "landing"
    })


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Compute real metrics strictly from database records
    active_watches_count = db.query(Watch).filter(Watch.user_id == user.id, Watch.status == "active").count()
    total_watches_count = db.query(Watch).filter(Watch.user_id == user.id).count()
    total_notifs = db.query(Notification).filter(Notification.user_id == user.id).count()
    unread_notifs = db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == False).count()

    # Recent notifications
    recent_notifs_records = db.query(Notification).filter(
        Notification.user_id == user.id
    ).order_by(Notification.created_at.desc()).limit(5).all()

    recent_notifications = []
    for n in recent_notifs_records:
        ev = db.query(Event).filter(Event.id == n.event_id).first()
        w = db.query(Watch).filter(Watch.id == n.watch_id).first()
        if ev and w:
            recent_notifications.append({
                "id": n.id,
                "event_id": ev.id,
                "event_headline": ev.headline,
                "event_summary": ev.summary,
                "watch_title": w.title,
                "created_at": n.created_at,
            })

    # Recent watches
    recent_watches = db.query(Watch).filter(
        Watch.user_id == user.id
    ).order_by(Watch.updated_at.desc()).limit(5).all()

    next_digest_str = f"{user.digest_time or '08:00'} ({user.digest_frequency.capitalize() if user.digest_frequency != 'none' else 'Disabled'})"

    metrics = {
        "active_watches": active_watches_count,
        "total_watches": total_watches_count,
        "total_notifications": total_notifs,
        "unread_notifications": unread_notifs,
        "next_digest_time": next_digest_str,
    }

    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "current_user": user,
        "active_page": "dashboard",
        "unread_notifications_count": unread_notifs,
        "metrics": metrics,
        "recent_notifications": recent_notifications,
        "recent_watches": recent_watches,
    })
