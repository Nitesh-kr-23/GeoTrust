from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    google_places_api_key: str = ""
    google_places_base_url: str = "https://places.googleapis.com/v1"

    database_url: str = "sqlite:///./geotrust.db"

    default_search_radius_m: int = 4000  # 3-5 km as per project spec
    max_results_returned: int = 3        

    trust_model_path: str = "ml/trust_model.joblib"
    pricing_model_dir: str = "ml"

    environment: str = "development"

    cors_allowed_origins: str = ""

    rate_limit_per_minute: int = 30

    @property
    def cors_origins_list(self) -> list[str]:
        if self.environment != "production":
            return ["*"]
        origins = [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]
        return origins or []  

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()
