import json
import logging
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Watch, Event, WatchMatch, Feedback, Notification
from app.schemas.watch import StructuredWatchRules
from app.services.watch_parser import parse_watch_prompt
from app.jobs.monitoring_job import run_watch_monitoring

logger = logging.getLogger("worldamaze.watches_router")
router = APIRouter(tags=["Watches"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/watches", response_class=HTMLResponse)
def list_watches(
    request: Request,
    status: Optional[str] = None,
    q: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Watch).filter(Watch.user_id == user.id)

    # Status filter
    current_filter = "all"
    if status in ("active", "paused", "archived"):
        query = query.filter(Watch.status == status)
        current_filter = status

    # Search filter
    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.filter((Watch.title.ilike(term)) | (Watch.description.ilike(term)))

    watches = query.order_by(Watch.created_at.desc()).all()

    # Filter tab counts
    all_count = db.query(Watch).filter(Watch.user_id == user.id).count()
    active_count = db.query(Watch).filter(Watch.user_id == user.id, Watch.status == "active").count()
    paused_count = db.query(Watch).filter(Watch.user_id == user.id, Watch.status == "paused").count()
    archived_count = db.query(Watch).filter(Watch.user_id == user.id, Watch.status == "archived").count()
    unread_notifs = db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == False).count()

    return templates.TemplateResponse(request=request, name="watches/index.html", context={
        "current_user": user,
        "active_page": "watches",
        "unread_notifications_count": unread_notifs,
        "watches": watches,
        "current_filter": current_filter,
        "search_query": q,
        "counts": {
            "all": all_count,
            "active": active_count,
            "paused": paused_count,
            "archived": archived_count,
        }
    })


@router.post("/watches/interpret", response_class=HTMLResponse)
def interpret_prompt(
    request: Request,
    prompt: str = Form(...),
    user: User = Depends(get_current_user)
):
    """
    Interprets natural language monitoring prompt using Groq GPT-OSS 120B
    and returns editable confirmation HTML card.
    """
    clean_prompt = prompt.strip()
    if len(clean_prompt) < 5:
        return HTMLResponse("<div class='p-3 bg-red-50 text-red-700 text-xs rounded'>Prompt is too short. Please describe the event or condition in more detail.</div>", status_code=400)

    rules = parse_watch_prompt(clean_prompt)
    return templates.TemplateResponse(request=request, name="components/parsed_rule_card.html", context={
        "rules": rules
    })


@router.post("/watches")
def create_watch(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    subjects: str = Form(""),
    include_terms: str = Form(""),
    exclude_terms: str = Form(""),
    trigger_conditions: str = Form(""),
    event_categories: str = Form("announcement, confirmation, policy"),
    evidence_requirement: str = Form("any_report"),
    uncertainty_policy: str = Form("flag_unverified"),
    importance_threshold: str = Form("medium"),
    delivery_mode: str = Form("immediate"),
    polling_interval_minutes: int = Form(30),
    digest_time: str = Form("08:00"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Saves confirmed watch to database and triggers initial monitoring check."""
    # Build structured rules dictionary
    rules_obj = StructuredWatchRules(
        title=title.strip(),
        description=description.strip(),
        subjects=[s.strip() for s in subjects.split(",") if s.strip()],
        include_terms=[s.strip() for s in include_terms.split(",") if s.strip()],
        exclude_terms=[s.strip() for s in exclude_terms.split(",") if s.strip()],
        trigger_conditions=[s.strip() for s in trigger_conditions.replace("\r", "").split("\n") if s.strip()],
        event_categories=[s.strip() for s in event_categories.split(",") if s.strip()],
        importance_threshold=importance_threshold,
        evidence_requirement=evidence_requirement,
        uncertainty_policy=uncertainty_policy,
        delivery_mode=delivery_mode,
        digest_time=digest_time,
        polling_interval=polling_interval_minutes,
        status="active"
    )

    new_watch = Watch(
        user_id=user.id,
        title=title.strip(),
        description=description.strip(),
        structured_rules=json.dumps(rules_obj.model_dump()),
        status="active",
        delivery_mode=delivery_mode,
        polling_interval_minutes=polling_interval_minutes,
    )
    db.add(new_watch)
    db.commit()
    db.refresh(new_watch)

    # Proactively run initial check for newly created watch
    try:
        run_watch_monitoring(new_watch.id, trigger_type="initial_setup")
    except Exception as e:
        logger.warning(f"Initial check for watch {new_watch.id} deferred: {e}")

    return RedirectResponse(url=f"/watches/{new_watch.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/watches/{watch_id}", response_class=HTMLResponse)
def get_watch_detail(
    watch_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    watch = db.query(Watch).filter(Watch.id == watch_id, Watch.user_id == user.id).first()
    if not watch:
        raise HTTPException(status_code=404, detail="Watch not found or unauthorized")

    rules = watch.rules_dict

    # Matched events
    matches = db.query(WatchMatch).filter(WatchMatch.watch_id == watch.id).order_by(WatchMatch.created_at.desc()).all()
    matched_events = []
    for m in matches:
        ev = db.query(Event).filter(Event.id == m.event_id).first()
        if ev:
            matched_events.append({"event": ev, "match": m})

    # Feedback history
    feedbacks = db.query(Feedback).filter(Feedback.watch_id == watch.id).order_by(Feedback.created_at.desc()).all()
    unread_notifs = db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == False).count()

    return templates.TemplateResponse(request=request, name="watches/detail.html", context={
        "current_user": user,
        "active_page": "watches",
        "unread_notifications_count": unread_notifs,
        "watch": watch,
        "rules": rules,
        "matched_events": matched_events,
        "feedbacks": feedbacks,
    })


@router.post("/watches/{watch_id}/update")
def update_watch(
    watch_id: str,
    title: str = Form(...),
    subjects: str = Form(""),
    include_terms: str = Form(""),
    exclude_terms: str = Form(""),
    evidence_requirement: str = Form("any_report"),
    importance_threshold: str = Form("medium"),
    uncertainty_policy: str = Form("flag_unverified"),
    delivery_mode: str = Form("immediate"),
    polling_interval_minutes: int = Form(30),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    watch = db.query(Watch).filter(Watch.id == watch_id, Watch.user_id == user.id).first()
    if not watch:
        raise HTTPException(status_code=404, detail="Watch not found or unauthorized")

    rules_dict = watch.rules_dict
    rules_dict["title"] = title.strip()
    rules_dict["subjects"] = [s.strip() for s in subjects.split(",") if s.strip()]
    rules_dict["include_terms"] = [s.strip() for s in include_terms.split(",") if s.strip()]
    rules_dict["exclude_terms"] = [s.strip() for s in exclude_terms.split(",") if s.strip()]
    rules_dict["evidence_requirement"] = evidence_requirement
    rules_dict["importance_threshold"] = importance_threshold
    rules_dict["uncertainty_policy"] = uncertainty_policy
    rules_dict["delivery_mode"] = delivery_mode
    rules_dict["polling_interval"] = polling_interval_minutes

    watch.title = title.strip()
    watch.delivery_mode = delivery_mode
    watch.polling_interval_minutes = polling_interval_minutes
    watch.structured_rules = json.dumps(rules_dict)
    db.commit()

    return RedirectResponse(url=f"/watches/{watch.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/watches/{watch_id}/pause")
def pause_watch(
    watch_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    watch = db.query(Watch).filter(Watch.id == watch_id, Watch.user_id == user.id).first()
    if not watch:
        raise HTTPException(status_code=404, detail="Watch not found or unauthorized")

    watch.status = "paused"
    db.commit()
    return RedirectResponse(url=f"/watches/{watch.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/watches/{watch_id}/resume")
def resume_watch(
    watch_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    watch = db.query(Watch).filter(Watch.id == watch_id, Watch.user_id == user.id).first()
    if not watch:
        raise HTTPException(status_code=404, detail="Watch not found or unauthorized")

    watch.status = "active"
    db.commit()
    return RedirectResponse(url=f"/watches/{watch.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/watches/{watch_id}/check")
def manual_check_watch(
    watch_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    watch = db.query(Watch).filter(Watch.id == watch_id, Watch.user_id == user.id).first()
    if not watch:
        raise HTTPException(status_code=404, detail="Watch not found or unauthorized")

    run_watch_monitoring(watch.id, trigger_type="manual")
    return RedirectResponse(url=f"/watches/{watch.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/watches/{watch_id}/delete")
def delete_watch(
    watch_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    watch = db.query(Watch).filter(Watch.id == watch_id, Watch.user_id == user.id).first()
    if not watch:
        raise HTTPException(status_code=404, detail="Watch not found or unauthorized")

    db.delete(watch)
    db.commit()
    return RedirectResponse(url="/watches", status_code=status.HTTP_303_SEE_OTHER)
