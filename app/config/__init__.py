import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Central application configuration loaded from environment variables."""

    # App
    APP_NAME: str = os.getenv("APP_NAME", "Document Intelligence Engine")
    APP_ENV: str = os.getenv("APP_ENV", "local")
    APP_DEBUG: bool = os.getenv("APP_DEBUG", "false").lower() == "true"
    TZ: str = os.getenv("TZ", "America/Mexico_City")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # File processing
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", 10))
    UPLOAD_FOLDER: str = os.getenv("UPLOAD_FOLDER", "uploads")

    # Allowed file extensions per processor
    ALLOWED_EXTENSIONS: set = {"pdf"}

    # Valid document types
    DOCUMENT_TYPES: set = {
        "ine",
        "csf",
        "comprobante_domicilio",
        "estado_cuenta",
        "licencia_profesional",
    }

    # Extractor
    DEFAULT_EXTRACTOR: str = os.getenv("DEFAULT_EXTRACTOR", "regex")
    DEFAULT_LANGUAGE: str = os.getenv("DEFAULT_LANGUAGE", "es")