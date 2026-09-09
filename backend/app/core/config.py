import os
from pydantic import BaseModel, Field, field_validator

class Settings(BaseModel):
    PROJECT_NAME: str = "GIVIN - Gujarat Integrated Video Intelligence Network"
    PROJECT_VERSION: str = "1.2.0"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development").lower()
    SECRET_KEY: str = Field(default_factory=lambda: os.getenv("SECRET_KEY", ""))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./givin.db")
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: [
        origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",") if origin.strip()
    ])
    GIVIN_VISION_MODE: str = os.getenv("GIVIN_VISION_MODE", "auto").lower()
    GIVIN_STREAM_MODE: str = os.getenv("GIVIN_STREAM_MODE", "real").lower()
    EVIDENCE_DIR: str = os.getenv("GIVIN_EVIDENCE_DIR", "data/evidence")
    ANPR_CONFIDENCE_THRESHOLD: float = 0.75
    VEHICLE_CONFIDENCE_THRESHOLD: float = 0.70
    FUZZY_MATCH_DISTANCE_THRESHOLD: int = 1
    TOTAL_PLANNED_CAMERAS: int = 80000
    EDGE_COMPRESSION_RATIO: float = 0.05

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        if not value:
            if os.getenv("ENVIRONMENT", "development").lower() == "production":
                raise ValueError("SECRET_KEY is required in production")
            return "local-development-only-change-me"
        if len(value) < 32:
            raise ValueError("SECRET_KEY must contain at least 32 characters")
        return value

    @field_validator("GIVIN_VISION_MODE")
    @classmethod
    def validate_vision_mode(cls, value: str) -> str:
        if value not in {"real", "auto", "simulation"}:
            raise ValueError("GIVIN_VISION_MODE must be real, auto, or simulation")
        return value

settings = Settings()
