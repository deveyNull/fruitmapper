from functools import lru_cache
from pydantic_settings import BaseSettings
import os
from typing import Optional, List

class Settings(BaseSettings):
    # Base Configuration
    PROJECT_NAME: str = "Fruit Recipe Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "sqlite:///./app/fruit_platform.db"
    
    # Authentication
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Security
    COOKIE_SECURE: bool = os.getenv("ENVIRONMENT", "development") == "production"
    CORS_ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:8000",
        "http://localhost:3000",
    ]
    
    # File Upload
    UPLOAD_DIRECTORY: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")

    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()

# Optional: Keep the get_settings function for dependency injection
@lru_cache()
def get_settings() -> Settings:
    return settings