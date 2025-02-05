from fastapi import FastAPI, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.authentication import AuthenticationMiddleware

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
import uvicorn

from app.database import engine, Base
from app.config import get_settings
from app.routes import auth, fruits, fruit_types, recipes, groups, filters
from app.dependencies import get_current_user
from itsdangerous import URLSafeTimedSerializer
from typing import Optional
from app.models import User 



# Create instance of settings
settings = get_settings()

# Create all database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
)

app.add_middleware(
    AuthenticationMiddleware,
    backend=JWTAuthenticationBackend()
)





# Mount static files
#app.mount("/static", StaticFiles(directory="static"), name="static")

# Modify your Jinja2 templates initialization
templates = Jinja2Templates(directory="app/templates")


# Include all routers
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["auth"]
)

app.include_router(
    fruits.router,
    prefix=f"{settings.API_V1_STR}/fruits",
    tags=["fruits"]
)

app.include_router(
    fruit_types.router,
    prefix=f"{settings.API_V1_STR}/fruit-types",
    tags=["fruit_types"]
)

app.include_router(
    recipes.router,
    prefix=f"{settings.API_V1_STR}/recipes",
    tags=["recipes"]
)

app.include_router(
    groups.router,
    prefix=f"{settings.API_V1_STR}/groups",
    tags=["groups"]
)

app.include_router(
    filters.router,
    prefix=f"{settings.API_V1_STR}/filters",
    tags=["filters"]
)

# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )



@app.get("/")
async def root(
    request: Request, 
    current_user = User
):
    """Root endpoint - renders the home page"""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "current_user": current_user,
            # Add any other context variables you need
        }
    )

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