from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://realm:realm_secret@db:5432/realm"
    jwt_secret: str = "realm_jwt_secret_change_in_prod"
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 7
    news_api_key: str = "placeholder_key"

    class Config:
        env_file = ".env"


settings = Settings()
