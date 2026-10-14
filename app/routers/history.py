from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Event, EventArticle, Article, WatchMatch, Watch, Notification
from app.templates import templates

router = APIRouter(tags=["History"])


@router.get("/history", response_class=HTMLResponse)
def get_history_page(
    request: Request,
    q: Optional[str] = None,
    importance: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Event)

    # Search filter
    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.filter((Event.headline.ilike(term)) | (Event.summary.ilike(term)) | (Event.what_changed.ilike(term)))

    # Importance filter
    if importance in ("critical", "high", "medium", "low"):
        query = query.filter(Event.importance == importance)

    events = query.order_by(Event.first_detected_at.desc()).limit(50).all()
    unread_notifs = db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == False).count()

    return templates.TemplateResponse(request=request, name="history/index.html", context={
        "current_user": user,
        "active_page": "history",
        "unread_notifications_count": unread_notifs,
        "events": events,
        "search_query": q,
        "selected_importance": importance,
    })


@router.get("/history/{event_id}", response_class=HTMLResponse)
def get_event_detail(
    event_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Supporting articles
    ea_links = db.query(EventArticle).filter(EventArticle.event_id == event.id).all()
    supporting_articles = []
    primary_article = None
    for link in ea_links:
        art = db.query(Article).filter(Article.id == link.article_id).first()
        if art:
            supporting_articles.append(art)
            if link.is_primary or not primary_article:
                primary_article = art

    # Matches with watches belonging to this user
    matches = db.query(WatchMatch).join(Watch).filter(
        WatchMatch.event_id == event.id,
        Watch.user_id == user.id
    ).all()

    unread_notifs = db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == False).count()

    return templates.TemplateResponse(request=request, name="history/detail.html", context={
        "current_user": user,
        "active_page": "history",
        "unread_notifications_count": unread_notifs,
        "event": event,
        "primary_article": primary_article,
        "supporting_articles": supporting_articles,
        "matches": matches,
    })
