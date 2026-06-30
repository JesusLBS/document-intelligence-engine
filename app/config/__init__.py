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

    # AI Provider
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "gemini")

    # Groq
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GROQ_API_URL: str = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")

    # Gemini
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    GEMINI_API_URL: str = os.getenv("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta/models")

    # Document default fields per type
    DOCUMENT_DEFAULT_FIELDS: dict = {
        "ine": ["nombre", "apellido_paterno", "apellido_materno", "curp", "fecha_nacimiento", "fecha_vencimiento", "clave_elector"],
        "csf": ["rfc", "curp", "full_name", "padron_status", "tax_regimes"],
        "comprobante_domicilio": ["nombre", "direccion", "periodo", "fecha_emision", "empresa"],
    }