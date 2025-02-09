from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.authentication import (
    AuthenticationBackend, AuthenticationError, SimpleUser, 
    UnauthenticatedUser, AuthCredentials
)
from datetime import timedelta
from typing import Optional
import jwt

from app.database import get_db
import app.crud as crud
import app.schemas as schemas
from app.config import settings
from app.dependencies import get_current_user, create_access_token
from app.models import User

router = APIRouter()  # Remove the prefix here since it's added in main.py
templates = Jinja2Templates(directory="app/templates")

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Render the login page."""
    if request.user.is_authenticated:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        "login.html", 
        {
            "request": request,
            "error": request.query_params.get("error")
        }
    )

@router.post("/login")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        return RedirectResponse(
            url="/auth/login?error=Invalid+username+or+password",
            status_code=status.HTTP_303_SEE_OTHER
        )
    
    access_token = create_access_token(data={"sub": user.username})
    
    response = RedirectResponse(
        url="/",
        status_code=status.HTTP_303_SEE_OTHER
    )
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=settings.COOKIE_SECURE,
        samesite="lax"
    )
    
    return response

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Render the register page."""
    if request.user.is_authenticated:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        "register.html", 
        {
            "request": request,
            "error": request.query_params.get("error")
        }
    )

@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_db),
):
    if password != password_confirm:
        return RedirectResponse(
            url="/auth/register?error=Passwords+do+not+match",
            status_code=status.HTTP_303_SEE_OTHER
        )

    # Create user schema
    try:
        user = schemas.UserCreate(
            username=username,
            email=email,
            password=password
        )
    except ValueError as e:
        return RedirectResponse(
            url=f"/auth/register?error={str(e)}",
            status_code=status.HTTP_303_SEE_OTHER
        )

    # Check for existing user
    if crud.get_user_by_username(db, user.username):
        return RedirectResponse(
            url="/auth/register?error=Username+already+registered",
            status_code=status.HTTP_303_SEE_OTHER
        )
    
    if crud.get_user_by_email(db, user.email):
        return RedirectResponse(
            url="/auth/register?error=Email+already+registered",
            status_code=status.HTTP_303_SEE_OTHER
        )
    
    # Create user
    user = crud.create_user(db, user)
    
    # Create access token
    access_token = create_access_token(data={"sub": user.username})
    
    # Create response with cookie
    response = RedirectResponse(
        url="/",
        status_code=status.HTTP_303_SEE_OTHER
    )
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=settings.COOKIE_SECURE,
        samesite="lax"
    )
    
    return response

@router.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(
        url="/",
        status_code=status.HTTP_303_SEE_OTHER
    )
    response.delete_cookie(
        key="access_token",
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite="lax"
    )
    return response

@router.get("/me", response_model=schemas.UserResponse)
async def read_users_me(current_user = Depends(get_current_user)):
    return current_user

@router.put("/me", response_model=schemas.UserResponse)
async def update_user_me(
    user_update: schemas.UserUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.update_user(db, current_user.id, user_update)

@router.post("/password")
async def change_password(
    password_change: schemas.PasswordChange,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not crud.verify_password(db, current_user.id, password_change.old_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )
    
    crud.update_password(db, current_user.id, password_change.new_password)
    return {"message": "Password updated successfully"}