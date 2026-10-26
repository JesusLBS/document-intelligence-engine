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
    }

    # Extractor
    EXTRACTOR_STRATEGIES: set = {"regex", "ai"}
    DEFAULT_EXTRACTOR: str = os.getenv("DEFAULT_EXTRACTOR", "regex")

    # Types with no regex extractor: layouts vary too much (photographed cards, one bill format per provider).
    # They default to extractor=ai, and an explicit extractor=regex is rejected by request validation.
    AI_ONLY_DOCUMENT_TYPES: set = {"ine", "comprobante_domicilio"}

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
        "ine": [
            "nombre", "apellido_materno", "apellido_paterno", "curp", "fecha_nacimiento", "fecha_vencimiento",
            "clave_elector", "documento_detectado",
        ],
        "csf": ["rfc", "curp", "full_name", "padron_status", "tax_regimes"],
        "comprobante_domicilio": [
            "nombre_titular", "domicilio_completo", "calle", "numero_exterior", "numero_interior", "colonia",
            "municipio", "estado", "codigo_postal", "proveedor", "tipo_servicio", "numero_servicio",
            "fecha_emision", "periodo_inicio", "periodo_fin", "fecha_limite_pago",
        ],
    }

    # Meaning and format of each field, added to the AI prompt so every provider returns the same shape.
    # Dates are requested as printed and converted to ISO by the app (app/utils/date_normalizer.py, day first):
    # asked for ISO, a provider read 05/10/2026 month first and returned 2026-05-10, which the app can't detect.
    DOCUMENT_FIELD_DESCRIPTIONS: dict = {
        "ine": {
            "nombre": "given name(s) as printed (NOMBRE), without the surnames",
            "apellido_paterno": "first surname",
            "apellido_materno": "second surname, or null if the card shows only one",
            # Copied even when it looks malformed: OCR text often has one O/0 swap, which the app fixes
            # (id_normalizer); asked for a strict "18 characters", Groq returned null on 2 of 5 runs.
            "curp": "CURP (18 characters), copied as printed even if some characters look wrong; the app corrects OCR errors",
            "fecha_nacimiento": "date of birth (FECHA DE NACIMIENTO), exactly as printed",
            "fecha_vencimiento": "VIGENCIA exactly as printed (e.g. '2021-2031' or '2031')",
            "clave_elector": "CLAVE DE ELECTOR (18 characters), copied as printed even if some characters look wrong",
            # Observation, not a verdict (docs/decisions/0001): a rule compares it with the requested type.
            "documento_detectado": "which document the file actually is: ine, csf, comprobante_domicilio or otro",
        },
        "comprobante_domicilio": {
            "nombre_titular": "name of the account holder the bill is addressed to, as printed",
            "domicilio_completo": "full service address in one line: street, number, colonia, municipio, state and postal code",
            "calle": "street of the service address including its type as printed (CALLE, AV...), without the number",
            "numero_exterior": "exterior number of the service address",
            "numero_interior": "interior / apartment number, or null if there is none",
            "colonia": "colonia (neighborhood), without the 'COL.' prefix",
            "municipio": "municipio or alcaldía",
            "estado": "Mexican state (entidad federativa)",
            "codigo_postal": "5-digit postal code (C.P.)",
            "proveedor": "company that issued the bill (e.g. CFE, Telmex, Izzi, Totalplay, a water utility)",
            "tipo_servicio": "one of: luz, agua, gas, telefono, internet, television, otro "
                             "(a phone + internet bundle is internet)",
            "numero_servicio": "service, account or contract number that identifies the supply",
            "fecha_emision": "issue date of the bill, exactly as printed",
            "periodo_inicio": "first day of the billed period, exactly as printed",
            "periodo_fin": "last day of the billed period, exactly as printed",
            "fecha_limite_pago": "payment due date (fecha límite de pago), exactly as printed",
        },
    }

    @classmethod
    def default_extractor_for(cls, document_type: str) -> str:
        """
        Return the extractor strategy used when the request does not send one.

        Args:
            document_type (str): Registered document type.

        Returns:
            str: 'ai' for AI-only types, otherwise DEFAULT_EXTRACTOR.
        """
        if document_type in cls.AI_ONLY_DOCUMENT_TYPES:
            return "ai"
        return cls.DEFAULT_EXTRACTOR