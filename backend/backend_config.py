"""
Production-Grade Configuration for GutBot Backend

This module provides centralized configuration management for the backend server.
"""

import os
from dotenv import load_dotenv

load_dotenv()

class BackendConfig:
    """Backend configuration management"""
    
    # Server Configuration
    HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
    PORT = int(os.getenv("BACKEND_PORT", 5000))
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    THREADED = True
    
    # CORS Configuration
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    CORS_METHODS = ["GET", "POST", "OPTIONS", "DELETE", "PUT"]
    CORS_ALLOW_HEADERS = ["Content-Type", "Authorization"]
    
    # File Upload Configuration
    MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", 50 * 1024 * 1024))  # 50MB
    ALLOWED_EXTENSIONS = [".pdf"]
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
    
    # LLM Configuration
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "local")
    LLM_MODEL = os.getenv("LLM_MODEL", "local-llm")
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", 60))
    
    # Embedding Configuration
    EMBEDDING_MODEL = os.getenv(
        "EMBEDDING_MODEL", 
        "sentence-transformers/all-MiniLM-L6-v2"
    )
    
    # PDF Processing Configuration
    PDF_CHUNK_SIZE = int(os.getenv("PDF_CHUNK_SIZE", 500))
    PDF_CHUNK_OVERLAP = int(os.getenv("PDF_CHUNK_OVERLAP", 50))
    
    # Search Configuration
    SEARCH_TOP_K = int(os.getenv("SEARCH_TOP_K", 5))
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", 0.3))
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv(
        "LOG_FORMAT",
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Database Configuration (for future use)
    DATABASE_URL = os.getenv("DATABASE_URL", None)
    
    # Cache Configuration
    CACHE_ENABLED = os.getenv("CACHE_ENABLED", "False").lower() == "true"
    CACHE_TTL = int(os.getenv("CACHE_TTL", 3600))  # 1 hour
    
    # Rate Limiting
    RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "True").lower() == "true"
    RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", 100))
    RATE_LIMIT_PERIOD = int(os.getenv("RATE_LIMIT_PERIOD", 60))  # seconds
    
    # Security Configuration
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    }
    
    # API Configuration
    API_VERSION = "v1"
    API_PREFIX = f"/api/{API_VERSION}"
    
    @classmethod
    def validate(cls):
        """Validate configuration on startup"""
        errors = []
        
        if not os.path.exists(cls.UPLOAD_FOLDER):
            try:
                os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
            except Exception as e:
                errors.append(f"Failed to create upload folder: {e}")
        
        if errors:
            raise ValueError("\n".join(errors))
    
    @classmethod
    def get_config_dict(cls):
        """Get configuration as dictionary"""
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if not key.startswith("_") and key.isupper()
        }

class FrontendConfig:
    """Frontend configuration management"""
    
    # API Configuration
    API_URL = os.getenv("VITE_API_URL", "http://localhost:5000")
    API_TIMEOUT = int(os.getenv("VITE_API_TIMEOUT", 60000))
    
    # App Information
    APP_NAME = os.getenv("VITE_APP_NAME", "GutBot")
    APP_VERSION = os.getenv("VITE_APP_VERSION", "1.0.0")
    
    # Feature Flags
    ENABLE_ANALYTICS = os.getenv("VITE_ENABLE_ANALYTICS", "false").lower() == "true"
    DEBUG_MODE = os.getenv("VITE_DEBUG_MODE", "false").lower() == "true"
    
    # UI Configuration
    SIDEBAR_WIDTH = 280
    HEADER_HEIGHT = 80
    THEME = os.getenv("VITE_THEME", "light")
    
    # Upload Configuration
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_MIME_TYPES = ["application/pdf"]

class DevelopmentConfig(BackendConfig):
    """Development environment configuration"""
    DEBUG = True
    LOG_LEVEL = "DEBUG"

class ProductionConfig(BackendConfig):
    """Production environment configuration"""
    DEBUG = False
    LOG_LEVEL = "WARNING"
    CACHE_ENABLED = True
    RATE_LIMIT_ENABLED = True

class TestingConfig(BackendConfig):
    """Testing environment configuration"""
    DEBUG = True
    TESTING = True
    LOG_LEVEL = "DEBUG"
    MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB for testing

# Select appropriate configuration
ENV = os.getenv("FLASK_ENV", "development").lower()

if ENV == "production":
    config = ProductionConfig
elif ENV == "testing":
    config = TestingConfig
else:
    config = DevelopmentConfig

# Validate configuration on import
try:
    config.validate()
except Exception as e:
    import sys
    print(f"Configuration error: {e}", file=sys.stderr)
    sys.exit(1)
