from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Notification, Event, Watch, EventArticle, Article, Feedback
from app.templates import templates

router = APIRouter(tags=["Notifications"])


@router.get("/notifications", response_class=HTMLResponse)
def list_notifications(
    request: Request,
    status: Optional[str] = None,
    importance: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Notification).filter(Notification.user_id == user.id)

    current_filter = "all"
    if status == "unread":
        query = query.filter(Notification.is_read == False)
        current_filter = "unread"
    elif importance == "critical_high":
        current_filter = "critical_high"
        # Join with event to filter importance
        query = query.join(Event).filter(Event.importance.in_(["critical", "high"]))

    notifications_list = query.order_by(Notification.created_at.desc()).all()

    items = []
    for n in notifications_list:
        ev = db.query(Event).filter(Event.id == n.event_id).first()
        w = db.query(Watch).filter(Watch.id == n.watch_id).first()
        if not ev or not w:
            continue

        # Supporting sources
        ea_links = db.query(EventArticle).filter(EventArticle.event_id == ev.id).all()
        sources = []
        for l in ea_links:
            art = db.query(Article).filter(Article.id == l.article_id).first()
            if art:
                sources.append({"source_name": art.source_name, "url": art.canonical_url, "title": art.title})

        items.append({
            "notification": n,
            "event": ev,
            "watch": w,
            "sources": sources
        })

    all_count = db.query(Notification).filter(Notification.user_id == user.id).count()
    unread_count = db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == False).count()

    return templates.TemplateResponse(request=request, name="notifications/index.html", context={
        "current_user": user,
        "active_page": "notifications",
        "unread_notifications_count": unread_count,
        "notifications": items,
        "current_filter": current_filter,
        "counts": {
            "all": all_count,
            "unread": unread_count,
        }
    })


@router.post("/notifications/{notification_id}/toggle-read")
def toggle_read(
    notification_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    n = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user.id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")

    n.is_read = not n.is_read
    db.commit()
    return RedirectResponse(url="/notifications", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/notifications/mark-all-read")
def mark_all_read(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == False).update({"is_read": True})
    db.commit()
    return RedirectResponse(url="/notifications", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/feedback")
def submit_feedback(
    request: Request,
    watch_id: str = Form(...),
    event_id: Optional[str] = Form(None),
    notification_id: Optional[str] = Form(None),
    feedback_type: str = Form(...),
    comment: Optional[str] = Form(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    feedback = Feedback(
        user_id=user.id,
        watch_id=watch_id,
        event_id=event_id,
        notification_id=notification_id,
        feedback_type=feedback_type,
        comment=comment
    )
    db.add(feedback)
    db.commit()

    # Redirect back to referring page
    referer = request.headers.get("referer") or "/notifications"
    return RedirectResponse(url=referer, status_code=status.HTTP_303_SEE_OTHER)
