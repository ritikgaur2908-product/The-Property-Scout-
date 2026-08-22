import os
from dotenv import load_dotenv

# Load environment variables from .env file at the project root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

class Settings:
    # Service Information
    APP_NAME: str = "The Property Scout API"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

    # Databases
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/property_scout"
    ).strip()
    VECTOR_DB_URL: str = os.getenv("VECTOR_DB_URL", "http://localhost:6333").strip()
    VECTOR_DB_API_KEY: str = os.getenv("VECTOR_DB_API_KEY", "local-dev-key").strip()

    # AI configuration
    GROQ_API_KEY: str = (os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY") or "").strip()
    GEMINI_API_KEY: str = (os.getenv("GEMINI_API_KEY") or "").strip()

    # Voice configuration
    DEEPGRAM_API_KEY: str = (os.getenv("DEEPGRAM_API_KEY") or os.getenv("STT_API_KEY") or "").strip()
    PLAYHT_USER_ID: str = os.getenv("PLAYHT_USER_ID", "")
    PLAYHT_API_KEY: str = os.getenv("PLAYHT_API_KEY", "")

    # LLM Configurations
    LLM_API_KEY: str = (os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY") or "").strip()
    LLM_MODEL: str = os.getenv("LLM_MODEL", "openai/gpt-oss-120b").strip()

    # Voice APIs
    STT_API_KEY: str = (os.getenv("STT_API_KEY") or os.getenv("DEEPGRAM_API_KEY") or "").strip()
    TTS_API_KEY: str = os.getenv("TTS_API_KEY", "")

    # Webhooks & Email Notifications (N8N)
    N8N_WEBHOOK_BASE_URL: str = os.getenv("N8N_WEBHOOK_BASE_URL", "https://n8n.example.com/webhook")
    N8N_BOOKING_WEBHOOK_PATH: str = os.getenv("N8N_BOOKING_WEBHOOK_PATH", "/booking")
    N8N_SHORTLIST_WEBHOOK_PATH: str = os.getenv("N8N_SHORTLIST_WEBHOOK_PATH", "/shortlist")
    SENDER_EMAIL: str = os.getenv("SENDER_EMAIL", "noreply@thepropertyscout.in")

    # OpenStreetMap MCP
    OSM_MCP_ENDPOINT: str = os.getenv("OSM_MCP_ENDPOINT", "http://localhost:8080")

settings = Settings()
