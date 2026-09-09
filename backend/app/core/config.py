import os
from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "GIVIN - Gujarat Integrated Video Intelligence Network"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "givin_super_secret_production_key_gujarat_police_2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./givin.db")
    
    # AI / Detection thresholds
    ANPR_CONFIDENCE_THRESHOLD: float = 0.75
    VEHICLE_CONFIDENCE_THRESHOLD: float = 0.70
    FUZZY_MATCH_DISTANCE_THRESHOLD: int = 1
    
    # Scale simulation parameters
    TOTAL_PLANNED_CAMERAS: int = 80000
    EDGE_COMPRESSION_RATIO: float = 0.05  # 95% bandwidth saved by sending metadata centrally

settings = Settings()
