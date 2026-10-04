"""
NYAYASHASTRA - Configuration Management
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = True
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://localhost:8080,http://localhost:8081,http://localhost:8082,http://localhost:8083,http://localhost:8084,http://localhost:8085"
    
    # Database
    database_url: str = "sqlite:///./nyayguru.db"  # Default to SQLite for easy setup
    database_echo: bool = False
    
    # Vector Database
    chroma_persist_dir: str = "./chroma_db"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"  # Changed to smaller model to prevent OOM
    
    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4-turbo-preview"
    openai_embedding_model: str = "text-embedding-3-small"
    
    # Groq API (fast LLM inference)
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    
    # Gemini API
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    
    # Local LLM
    use_local_llm: bool = False
    local_llm_endpoint: str = "http://localhost:11434/api"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    use_cache: bool = False
    
    # Document Processing
    max_upload_size_mb: int = 10
    allowed_extensions: str = "pdf,doc,docx"
    
    # Security
    secret_key: str = "nyayashastra-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Clerk Authentication
    clerk_secret_key: str = ""
    
    # SMTP Email Configuration
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@nyayashastra.com"
    smtp_from_name: str = "NyayaShastra Legal Services"

    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def allowed_extensions_list(self) -> List[str]:
        return [ext.strip() for ext in self.allowed_extensions.split(",")]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env


# Global settings instance
settings = Settings()
