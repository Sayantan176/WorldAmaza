import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Watch, Event, Notification, Digest, Feedback
from app.schemas.watch import (
    WatchPromptRequest,
    StructuredWatchRules,
    WatchCreateRequest,
    WatchUpdateRequest,
    WatchResponse,
)
from app.schemas.event import EventResponse
from app.schemas.notification import NotificationResponse, NotificationUpdate
from app.schemas.digest import DigestResponse
from app.schemas.feedback import FeedbackCreateRequest, FeedbackResponse
from app.schemas.user import UserResponse, UserSettingsUpdate
from app.services.watch_parser import parse_watch_prompt
from app.jobs.monitoring_job import run_watch_monitoring
from app.config import settings

router = APIRouter(prefix="/api/v1", tags=["REST API"])


# 1. Dashboard Metrics
@router.get("/dashboard")
def api_dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    active_watches = db.query(Watch).filter(Watch.user_id == user.id, Watch.status == "active").count()
    total_watches = db.query(Watch).filter(Watch.user_id == user.id).count()
    total_notifs = db.query(Notification).filter(Notification.user_id == user.id).count()
    unread_notifs = db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == False).count()
    
    return {
        "active_watches": active_watches,
        "total_watches": total_watches,
        "total_notifications": total_notifs,
        "unread_notifications": unread_notifs,
        "digest_schedule": {
            "frequency": user.digest_frequency,
            "time": user.digest_time,
            "timezone": user.timezone,
        }
    }


# 2. Watch Interpret
@router.post("/watches/interpret", response_model=StructuredWatchRules)
def api_interpret_watch(payload: WatchPromptRequest, user: User = Depends(get_current_user)):
    return parse_watch_prompt(payload.prompt)


# 3. Watches CRUD
@router.post("/watches", response_model=WatchResponse, status_code=status.HTTP_201_CREATED)
def api_create_watch(payload: WatchCreateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    watch = Watch(
        user_id=user.id,
        title=payload.title,
        description=payload.description,
        structured_rules=json.dumps(payload.rules.model_dump()),
        status="active",
        delivery_mode=payload.delivery_mode or "immediate",
        polling_interval_minutes=payload.polling_interval or 30,
    )
    db.add(watch)
    db.commit()
    db.refresh(watch)

    # Initial check
    try:
        run_watch_monitoring(watch.id, trigger_type="initial_setup")
    except Exception:
        pass

    return WatchResponse(
        id=watch.id,
        user_id=watch.user_id,
        title=watch.title,
        description=watch.description,
        structured_rules=watch.rules_dict,
        status=watch.status,
        delivery_mode=watch.delivery_mode,
        polling_interval_minutes=watch.polling_interval_minutes,
        last_checked_at=watch.last_checked_at,
        last_matched_at=watch.last_matched_at,
        events_count=watch.events_count,
        created_at=watch.created_at,
        updated_at=watch.updated_at,
    )


@router.get("/watches", response_model=List[WatchResponse])
def api_list_watches(
    status: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Watch).filter(Watch.user_id == user.id)
    if status in ("active", "paused", "archived"):
        query = query.filter(Watch.status == status)
    
    watches = query.order_by(Watch.created_at.desc()).all()
    return [
        WatchResponse(
            id=w.id,
            user_id=w.user_id,
            title=w.title,
            description=w.description,
            structured_rules=w.rules_dict,
            status=w.status,
            delivery_mode=w.delivery_mode,
            polling_interval_minutes=w.polling_interval_minutes,
            last_checked_at=w.last_checked_at,
            last_matched_at=w.last_matched_at,
            events_count=w.events_count,
            created_at=w.created_at,
            updated_at=w.updated_at,
        ) for w in watches
    ]


@router.get("/watches/{watch_id}", response_model=WatchResponse)
def api_get_watch(watch_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    watch = db.query(Watch).filter(Watch.id == watch_id, Watch.user_id == user.id).first()
    if not watch:
        raise HTTPException(status_code=404, detail="Watch not found")
    
    return WatchResponse(
        id=watch.id,
        user_id=watch.user_id,
        title=watch.title,
        description=watch.description,
        structured_rules=watch.rules_dict,
        status=watch.status,
        delivery_mode=watch.delivery_mode,
        polling_interval_minutes=watch.polling_interval_minutes,
        last_checked_at=watch.last_checked_at,
        last_matched_at=watch.last_matched_at,
        events_count=watch.events_count,
        created_at=watch.created_at,
        updated_at=watch.updated_at,
    )


@router.patch("/watches/{watch_id}", response_model=WatchResponse)
def api_update_watch(
    watch_id: str,
    payload: WatchUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    watch = db.query(Watch).filter(Watch.id == watch_id, Watch.user_id == user.id).first()
    if not watch:
        raise HTTPException(status_code=404, detail="Watch not found")

    if payload.title is not None:
        watch.title = payload.title
    if payload.status is not None:
        watch.status = payload.status
    if payload.delivery_mode is not None:
        watch.delivery_mode = payload.delivery_mode
    if payload.polling_interval_minutes is not None:
        watch.polling_interval_minutes = payload.polling_interval_minutes
    if payload.rules is not None:
        watch.structured_rules = json.dumps(payload.rules.model_dump())

    db.commit()
    db.refresh(watch)

    return WatchResponse(
        id=watch.id,
        user_id=watch.user_id,
        title=watch.title,
        description=watch.description,
        structured_rules=watch.rules_dict,
        status=watch.status,
        delivery_mode=watch.delivery_mode,
        polling_interval_minutes=watch.polling_interval_minutes,
        last_checked_at=watch.last_checked_at,
        last_matched_at=watch.last_matched_at,
        events_count=watch.events_count,
        created_at=watch.created_at,
        updated_at=watch.updated_at,
    )


@router.post("/watches/{watch_id}/pause")
def api_pause_watch(watch_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    watch = db.query(Watch).filter(Watch.id == watch_id, Watch.user_id == user.id).first()
    if not watch:
        raise HTTPException(status_code=404, detail="Watch not found")
    watch.status = "paused"
    db.commit()
    return {"message": "Watch paused successfully", "id": watch_id, "status": "paused"}


@router.post("/watches/{watch_id}/resume")
def api_resume_watch(watch_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    watch = db.query(Watch).filter(Watch.id == watch_id, Watch.user_id == user.id).first()
    if not watch:
        raise HTTPException(status_code=404, detail="Watch not found")
    watch.status = "active"
    db.commit()
    return {"message": "Watch resumed successfully", "id": watch_id, "status": "active"}


@router.post("/watches/{watch_id}/check")
def api_check_watch(watch_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    watch = db.query(Watch).filter(Watch.id == watch_id, Watch.user_id == user.id).first()
    if not watch:
        raise HTTPException(status_code=404, detail="Watch not found")
    
    result = run_watch_monitoring(watch.id, trigger_type="api_manual")
    return {"message": "Manual check completed", "result": result}


@router.delete("/watches/{watch_id}")
def api_delete_watch(watch_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    watch = db.query(Watch).filter(Watch.id == watch_id, Watch.user_id == user.id).first()
    if not watch:
        raise HTTPException(status_code=404, detail="Watch not found")
    db.delete(watch)
    db.commit()
    return {"message": "Watch deleted successfully", "id": watch_id}


# 4. Notifications
@router.get("/notifications", response_model=List[NotificationResponse])
def api_list_notifications(
    is_read: Optional[bool] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Notification).filter(Notification.user_id == user.id)
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)
    
    notifs = query.order_by(Notification.created_at.desc()).limit(100).all()
    results = []
    for n in notifs:
        ev = db.query(Event).filter(Event.id == n.event_id).first()
        w = db.query(Watch).filter(Watch.id == n.watch_id).first()
        results.append(NotificationResponse(
            id=n.id,
            user_id=n.user_id,
            watch_id=n.watch_id,
            event_id=n.event_id,
            is_read=n.is_read,
            delivery_channel=n.delivery_channel,
            email_sent=n.email_sent,
            email_status=n.email_status,
            email_error=n.email_error,
            created_at=n.created_at,
            event_headline=ev.headline if ev else None,
            event_summary=ev.summary if ev else None,
            event_importance=ev.importance if ev else None,
            event_evidence_status=ev.evidence_status if ev else None,
            watch_title=w.title if w else None,
        ))
    return results


@router.patch("/notifications/{notification_id}", response_model=NotificationResponse)
def api_update_notification(
    notification_id: str,
    payload: NotificationUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    n = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user.id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    n.is_read = payload.is_read
    db.commit()
    db.refresh(n)

    ev = db.query(Event).filter(Event.id == n.event_id).first()
    w = db.query(Watch).filter(Watch.id == n.watch_id).first()

    return NotificationResponse(
        id=n.id,
        user_id=n.user_id,
        watch_id=n.watch_id,
        event_id=n.event_id,
        is_read=n.is_read,
        delivery_channel=n.delivery_channel,
        email_sent=n.email_sent,
        email_status=n.email_status,
        email_error=n.email_error,
        created_at=n.created_at,
        event_headline=ev.headline if ev else None,
        event_summary=ev.summary if ev else None,
        event_importance=ev.importance if ev else None,
        event_evidence_status=ev.evidence_status if ev else None,
        watch_title=w.title if w else None,
    )


@router.post("/notifications/mark-all-read")
def api_mark_all_read(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    count = db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == False).update({"is_read": True})
    db.commit()
    return {"message": f"Marked {count} notifications as read"}


# 5. Feedback
@router.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def api_submit_feedback(payload: FeedbackCreateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    fb = Feedback(
        user_id=user.id,
        watch_id=payload.watch_id,
        event_id=payload.event_id,
        notification_id=payload.notification_id,
        feedback_type=payload.feedback_type,
        comment=payload.comment,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)

    return FeedbackResponse(
        id=fb.id,
        user_id=fb.user_id,
        watch_id=fb.watch_id,
        event_id=fb.event_id,
        notification_id=fb.notification_id,
        feedback_type=fb.feedback_type,
        comment=fb.comment,
        created_at=fb.created_at,
    )


# 6. History & Events
@router.get("/history", response_model=List[EventResponse])
def api_list_history(
    q: Optional[str] = None,
    importance: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Event)
    if q:
        term = f"%{q.strip()}%"
        query = query.filter((Event.headline.ilike(term)) | (Event.summary.ilike(term)))
    if importance in ("critical", "high", "medium", "low"):
        query = query.filter(Event.importance == importance)

    events = query.order_by(Event.first_detected_at.desc()).limit(50).all()
    return [
        EventResponse(
            id=e.id,
            dedup_key=e.dedup_key,
            headline=e.headline,
            summary=e.summary,
            event_category=e.event_category,
            importance=e.importance,
            evidence_status=e.evidence_status,
            what_changed=e.what_changed,
            first_detected_at=e.first_detected_at,
            last_updated_at=e.last_updated_at,
            status=e.status,
        ) for e in events
    ]


@router.get("/events/{event_id}", response_model=EventResponse)
def api_get_event(event_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventResponse(
        id=event.id,
        dedup_key=event.dedup_key,
        headline=event.headline,
        summary=event.summary,
        event_category=event.event_category,
        importance=event.importance,
        evidence_status=event.evidence_status,
        what_changed=event.what_changed,
        first_detected_at=event.first_detected_at,
        last_updated_at=event.last_updated_at,
        status=event.status,
    )


# 7. Digests
@router.get("/digests", response_model=List[DigestResponse])
def api_list_digests(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    digests = db.query(Digest).filter(Digest.user_id == user.id).order_by(Digest.created_at.desc()).limit(20).all()
    return [
        DigestResponse(
            id=d.id,
            user_id=d.user_id,
            title=d.title,
            period=d.period,
            event_count=d.event_count,
            content=d.content,
            email_sent=d.email_sent,
            email_status=d.email_status,
            email_error=d.email_error,
            created_at=d.created_at,
        ) for d in digests
    ]


# 8. Settings
@router.get("/settings", response_model=UserResponse)
def api_get_settings(user: User = Depends(get_current_user)):
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        timezone=user.timezone,
        email_notifications_enabled=user.email_notifications_enabled,
        digest_frequency=user.digest_frequency,
        digest_time=user.digest_time,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.patch("/settings", response_model=UserResponse)
def api_update_settings(
    payload: UserSettingsUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.timezone is not None:
        user.timezone = payload.timezone
    if payload.email_notifications_enabled is not None:
        user.email_notifications_enabled = payload.email_notifications_enabled
    if payload.digest_frequency is not None:
        user.digest_frequency = payload.digest_frequency
    if payload.digest_time is not None:
        user.digest_time = payload.digest_time

    db.commit()
    db.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        timezone=user.timezone,
        email_notifications_enabled=user.email_notifications_enabled,
        digest_frequency=user.digest_frequency,
        digest_time=user.digest_time,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
