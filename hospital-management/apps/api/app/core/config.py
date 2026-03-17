from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "hospital-api"
    app_env: str = "dev"
    api_port: int = 8000
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/hospital_dev"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-this-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    log_level: str = "INFO"
    request_log_enabled: bool = True
    rate_limit_enabled: bool = True
    rate_limit_login_per_minute: int = 20
    rate_limit_write_per_minute: int = 120
    rate_limit_bootstrap_per_hour: int = 5

    @property
    def cors_origins_list(self) -> list[str]:
        origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        if self.app_env in {"staging", "prod"} and not origins:
            raise ValueError("CORS_ORIGINS must be set for staging/prod")
        return origins


settings = Settings()
