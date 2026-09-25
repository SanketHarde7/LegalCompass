from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    # API & Server Meta
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "LegalCompass Backend API"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    ENVIRONMENT: str = "development"

    # CORS Configuration
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "*",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, str) and v.startswith("["):
            try:
                parsed = json.loads(v)
                return [str(i).strip() for i in parsed]
            except Exception:
                return ["*"]
        elif isinstance(v, list):
            return v
        return ["*"]

    # Google Gemini API Settings (Dynamic from .env)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL_ID: str = "gemini-3.5-flash-lite"

    # Groq Cloud API Settings (Dynamic from .env)
    GROQ_API_KEY: str = ""
    GROQ_MODEL_ID: str = "openai/gpt-oss-20b"

    # OpenRouter API Settings (Dynamic from .env)
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL_ID: str = "nvidia/nemotron-3.5-lightning:free"

    # Failover and provider preferences: e.g. "groq,gemini,openrouter"
    LLM_PROVIDER_ORDER: str = "groq,gemini,openrouter"

    # Local ONNX Embedding Model (FastEmbed CPU)
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"

    # Upload Constraints (25MB max per docs/contracts.md)
    MAX_UPLOAD_SIZE_BYTES: int = 26_214_400

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
