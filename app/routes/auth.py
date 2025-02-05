
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates


from fastapi.responses import HTMLResponse, RedirectResponse


from datetime import timedelta
from typing import Optional
import jwt

from app.database import get_db
import app.crud
import app.schemas
from app.config import settings
from app.dependencies import get_current_user, create_access_token
from app.models import User 
import app.templates



router = APIRouter(prefix="/auth", tags=["authentication"])

@router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user = User
):
    """
    Render the register page.
    Redirects authenticated users away from register page.
    """
    #  TODO: If user is already authenticated, redirect to home or dashboard
    #if current_user:
    #    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        "register.html", 
        {
            "request": request,
            "current_user": current_user,
            # Optional: Add any additional context needed for login page
            "error": request.query_params.get("error")  # Optional error handling
        }
    )
    


@router.post("/register")
async def register(
    response: Response,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_db),
):
    # Create a Pydantic model instance manually
    user = app.schemas.UserCreate(
        username=username,
        email=email,
        password=password,
        password_confirm=password_confirm
    )
    
    # Check if username exists
    if app.crud.get_user_by_username(db, user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email exists
    if app.crud.get_user_by_email(db, user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    output = app.crud.create_user(db, user)
    #TODO congrats registered
    #return RedirectResponse(url="/api/v1/auth/auth/login", status_code=status.HTTP_302_FOUND)
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    # Set cookie with token
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=settings.COOKIE_SECURE,  # True in production
        samesite="lax"
    )
    
    #return {"access_token": access_token, "token_type": "bearer"}
    return RedirectResponse(
        url="/", 
        status_code=status.HTTP_303_SEE_OTHER
    )

templates = Jinja2Templates(directory="app/templates")

@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user = User
):
    """
    Render the login page.
    Redirects authenticated users away from login page.
    """
    #  TODO: If user is already authenticated, redirect to home or dashboard
    #if current_user:
    #    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        "login.html", 
        {
            "request": request,
            "current_user": current_user,
            # Optional: Add any additional context needed for login page
            "error": request.query_params.get("error")  # Optional error handling
        }
    )


@router.post("/login")
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = app.crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    # Set cookie with token
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=settings.COOKIE_SECURE,  # True in production
        samesite="lax"
    )
    
    #return {"access_token": access_token, "token_type": "bearer"}
    return RedirectResponse(
        url="/", 
        status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/logout")
async def logout(response: Response):
    # Explicitly delete the cookie with more comprehensive settings
    response.delete_cookie(
        key="access_token", 
        path="/",  # Ensure you specify the path
        domain=None,  # Use None for current domain
        secure=True,  # If using HTTPS
        httponly=True  # Recommended for security
    )
    
    # Create a response that explicitly clears the cookie
    redirect_response = RedirectResponse(
        url="/", 
        status_code=status.HTTP_303_SEE_OTHER
    )
    
    # Additional method to ensure cookie deletion
    redirect_response.delete_cookie(
        key="access_token",
        path="/",
        domain=None,
        secure=True,
        httponly=True
    )
    return RedirectResponse(
        url="/", 
        status_code=status.HTTP_303_SEE_OTHER
    )

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token")
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=app.schemas.UserResponse)
async def read_users_me(
    current_user: app.schemas.UserResponse = Depends(get_current_user)
):
    return current_user

@router.put("/me", response_model=app.schemas.UserResponse)
async def update_user_me(
    user_update: app.schemas.UserUpdate,
    current_user: app.schemas.UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return app.crud.update_user(db, current_user.id, user_update)

@router.post("/password")
async def change_password(
    password_change: app.schemas.PasswordChange,
    current_user: app.schemas.UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify old password
    if not app.crud.verify_password(db, current_user.id, password_change.old_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )
    
    # Update password
    app.crud.update_password(db, current_user.id, password_change.new_password)
    return {"message": "Password updated successfully"}