from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # MongoDB
    MONGO_URI: str = "mongodb://localhost:27017/"
    DATABASE_NAME: str = "Linkedin"
    COLLECTION_NAME: str = "profile_data"
    
    # LinkedIn
    LINKEDIN_EMAIL: str
    LINKEDIN_PASSWORD: str
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    SECRET_KEY: str
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:4200"
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
