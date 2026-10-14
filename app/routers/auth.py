from fastapi import APIRouter, Request, Depends, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user_optional
from app.services.auth_service import auth_service, create_session_token, COOKIE_NAME

router = APIRouter(tags=["Authentication"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user=Depends(get_current_user_optional)):
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request=request, name="login.html", context={"error": None})


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user, err = auth_service.authenticate_user(db, email, password)
    if err or not user:
        return templates.TemplateResponse(request=request, name="login.html", context={"error": err or "Invalid credentials"}, status_code=400)

    token = create_session_token(user.id, user.email)
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,  # Can be true in production with HTTPS
        max_age=7 * 24 * 3600
    )
    return response


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, user=Depends(get_current_user_optional)):
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request=request, name="register.html", context={"error": None})


@router.post("/register", response_class=HTMLResponse)
def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(None),
    timezone: str = Form("UTC"),
    db: Session = Depends(get_db)
):
    user, err = auth_service.register_user(db, email, password, full_name, timezone)
    if err or not user:
        return templates.TemplateResponse(request=request, name="register.html", context={"error": err}, status_code=400)

    token = create_session_token(user.id, user.email)
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=7 * 24 * 3600
    )
    return response


@router.get("/logout")
@router.post("/logout")
def logout(request: Request):
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(COOKIE_NAME)
    return response
