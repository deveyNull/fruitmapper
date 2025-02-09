# File: app/main.py
from fastapi import FastAPI, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.authentication import (
    AuthenticationBackend, AuthenticationError, SimpleUser, 
    UnauthenticatedUser, AuthCredentials
)
import jwt
from jwt import PyJWTError
import uvicorn

from app.utils.messages import get_flashed_messages
from app.database import engine, Base, get_db
from app.config import settings
from app.routes import auth, fruits, fruit_types, recipes, groups, filters
from app.dependencies import get_current_user
import app.crud as crud

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="A platform for managing fruit recipes and associations"
)

# JWT Authentication Backend
class JWTAuthenticationBackend(AuthenticationBackend):
    async def authenticate(self, request):
        if "access_token" not in request.cookies:
            # Return None if no token (this makes request.user.is_authenticated = False)
            return None

        token = request.cookies["access_token"]
        if token.startswith("Bearer "):
            token = token[7:]

        try:
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=[settings.ALGORITHM]
            )
            username = payload.get("sub")
            if username is None:
                return None
            
            db = next(get_db())
            user = crud.get_user_by_username(db, username)
            if user is None:
                return None
            
            return AuthCredentials(["authenticated"]), SimpleUser(username)
        except jwt.PyJWTError:
            return None
        except Exception:
            return None

# Add middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    same_site="lax",
    https_only=settings.COOKIE_SECURE
)

app.add_middleware(
    AuthenticationMiddleware,
    backend=JWTAuthenticationBackend()
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Initialize templates
templates = Jinja2Templates(directory="app/templates")

# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )

@app.exception_handler(AuthenticationError)
async def auth_exception_handler(request: Request, exc: AuthenticationError):
    return RedirectResponse(
        url="/auth/login",
        status_code=status.HTTP_303_SEE_OTHER
    )

app.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"]
)

app.include_router(
    fruits.router,
    prefix="/fruits",  # This will handle /fruits routes
    tags=["fruits"]
)

app.include_router(
    fruit_types.router,
    prefix="/fruit-types",  # This will handle /fruit-types routes
    tags=["fruit_types"]
)

app.include_router(
    recipes.router,
    prefix="/recipes",  # This will handle /recipes routes
    tags=["recipes"]
)

app.include_router(
    groups.router,
    prefix="/groups",  # This will handle /groups routes
    tags=["groups"]
)

app.include_router(
    filters.router,
    prefix="/filters",  # This will handle /filters routes
    tags=["filters"]
)

@app.get("/", response_class=HTMLResponse)
async def root(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Render the home page
    Shows different content based on authentication status
    """
    context = {
        "request": request,
        "messages": get_flashed_messages(request)  # Add this line
    }
    
    # Add stats for authenticated users
    if request.user.is_authenticated:
        stats = {
            "total_recipes": crud.get_recipe_count(db),
            "total_types": crud.get_fruit_type_count(db),
            "total_filters": crud.get_filter_count(db, request.user.username)
        }
        context["stats"] = stats
    
    return templates.TemplateResponse("index.html", context)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.environment
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )