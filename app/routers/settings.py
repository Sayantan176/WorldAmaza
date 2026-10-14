from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Notification

router = APIRouter(tags=["Settings"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/settings", response_class=HTMLResponse)
def get_settings_page(
    request: Request,
    message: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    unread_notifs = db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == False).count()
    config_status = settings.safe_repr()

    return templates.TemplateResponse(request=request, name="settings/index.html", context={
        "current_user": user,
        "active_page": "settings",
        "unread_notifications_count": unread_notifs,
        "config_status": config_status,
        "message": message,
    })


@router.post("/settings/profile")
def update_profile(
    full_name: Optional[str] = Form(None),
    timezone: str = Form("UTC"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user.full_name = full_name.strip() if full_name else None
    user.timezone = timezone.strip()
    db.commit()
    return RedirectResponse(url="/settings?message=Profile+updated+successfully", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/settings/notifications")
def update_notifications(
    email_notifications_enabled: bool = Form(False),
    digest_frequency: str = Form("daily"),
    digest_time: str = Form("08:00"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user.email_notifications_enabled = email_notifications_enabled
    user.digest_frequency = digest_frequency
    user.digest_time = digest_time.strip()
    db.commit()
    return RedirectResponse(url="/settings?message=Notification+preferences+saved", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/settings/digest")
def update_digest_from_page(
    digest_frequency: str = Form("daily"),
    digest_time: str = Form("08:00"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user.digest_frequency = digest_frequency
    user.digest_time = digest_time.strip()
    db.commit()
    return RedirectResponse(url="/digests", status_code=status.HTTP_303_SEE_OTHER)
