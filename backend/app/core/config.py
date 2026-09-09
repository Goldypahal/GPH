import os
from typing import Optional
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
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "local").lower() # local | minio | s3
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "givinadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "change-this-development-password")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() in ("true", "1", "yes")
    MINIO_BUCKET_EVIDENCE: str = os.getenv("MINIO_BUCKET_EVIDENCE", "givin-evidence")
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: [
        origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",") if origin.strip()
    ])
    GIVIN_VISION_MODE: str = os.getenv("GIVIN_VISION_MODE", "auto").lower()
    GIVIN_STREAM_MODE: str = os.getenv("GIVIN_STREAM_MODE", "real").lower()
    GIVIN_VEHICLE_MODEL: str = os.getenv("GIVIN_VEHICLE_MODEL", "yolo11n.pt")
    GIVIN_PLATE_MODEL: str = os.getenv("GIVIN_PLATE_MODEL", "models/anpr_plate_detector.pt")
    GIVIN_OCR_MODEL: str = os.getenv("GIVIN_OCR_MODEL", "paddleocr")
    GIVIN_TRACKER_TYPE: str = os.getenv("GIVIN_TRACKER_TYPE", "bytetrack").lower()
    GIVIN_TEMPORAL_FUSION_WINDOW: int = int(os.getenv("GIVIN_TEMPORAL_FUSION_WINDOW", "10"))
    EVIDENCE_DIR: str = os.getenv("GIVIN_EVIDENCE_DIR", "data/evidence")
    ANPR_CONFIDENCE_THRESHOLD: float = 0.75
    VEHICLE_CONFIDENCE_THRESHOLD: float = 0.70
    FUZZY_MATCH_DISTANCE_THRESHOLD: int = 1
    TOTAL_PLANNED_CAMERAS: int = 80000
    EDGE_COMPRESSION_RATIO: float = 0.05
    OIDC_ENABLED: bool = os.getenv("OIDC_ENABLED", "true").lower() in ("true", "1", "yes")
    OIDC_ISSUER_URL: str = os.getenv("OIDC_ISSUER_URL", "https://sso.gujarat.gov.in/auth/realms/gujarat-police")
    OIDC_CLIENT_ID: str = os.getenv("OIDC_CLIENT_ID", "givin-c4i-platform")
    OIDC_JWKS_URL: Optional[str] = os.getenv("OIDC_JWKS_URL", None)
    OIDC_ALLOWED_ALGORITHMS: list[str] = ["RS256", "ES256"]
    DEV_BYPASS_TOKEN: str = os.getenv("DEV_BYPASS_TOKEN", "givin-local-dev-bypass-2026")

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
