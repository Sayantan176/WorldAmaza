from fastapi import APIRouter, Request, Depends, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Digest, Notification
from app.services.digest_service import digest_service
from app.templates import templates

router = APIRouter(tags=["Digests"])


@router.get("/digests", response_class=HTMLResponse)
def get_digests_page(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    preview = digest_service.compile_digest_preview(db, user, period=user.digest_frequency or "daily")
    past_digests = db.query(Digest).filter(Digest.user_id == user.id).order_by(Digest.created_at.desc()).limit(15).all()
    unread_notifs = db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == False).count()

    return templates.TemplateResponse(request=request, name="digests/index.html", context={
        "current_user": user,
        "active_page": "digests",
        "unread_notifications_count": unread_notifs,
        "preview": preview,
        "past_digests": past_digests,
    })


@router.post("/digests/generate")
def generate_digest_now(
    period: str = Form("daily"),
    force_send_email: bool = Form(False),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    digest_service.generate_and_deliver_digest(
        db=db,
        user=user,
        period=period,
        force_send_email=force_send_email
    )
    return RedirectResponse(url="/digests", status_code=status.HTTP_303_SEE_OTHER)
