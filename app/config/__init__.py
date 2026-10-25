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
    EXTRACTOR_STRATEGIES: set = {"regex", "ai"}
    DEFAULT_EXTRACTOR: str = os.getenv("DEFAULT_EXTRACTOR", "regex")

    # AI Provider (keep in sync with AiExtractor._resolve_provider)
    AI_PROVIDERS: set = {"gemini", "groq"}
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "gemini")

    # Groq (gpt-oss is a reasoning model; empty GROQ_REASONING_EFFORT omits reasoning params for non-reasoning models)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    GROQ_API_URL: str = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
    GROQ_REASONING_EFFORT: str = os.getenv("GROQ_REASONING_EFFORT", "low")
    GROQ_TIMEOUT_SECONDS: int = int(os.getenv("GROQ_TIMEOUT_SECONDS", 60))

    # Gemini (Gemini 3 uses thinkingLevel; empty GEMINI_THINKING_LEVEL omits it for models that don't support it)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    GEMINI_API_URL: str = os.getenv("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta/models")
    GEMINI_THINKING_LEVEL: str = os.getenv("GEMINI_THINKING_LEVEL", "low")
    GEMINI_TIMEOUT_SECONDS: int = int(os.getenv("GEMINI_TIMEOUT_SECONDS", 90))

    # Document default fields per type
    DOCUMENT_DEFAULT_FIELDS: dict = {
        "ine": ["nombre", "apellido_materno", "apellido_paterno", "curp", "fecha_nacimiento", "fecha_vencimiento", "clave_elector"],
        "csf": ["rfc", "curp", "full_name", "padron_status", "tax_regimes"],
        "comprobante_domicilio": ["nombre", "direccion", "periodo", "fecha_emision", "empresa"],
    }