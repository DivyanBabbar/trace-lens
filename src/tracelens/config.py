from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="TRACELENS_", extra="ignore")
    data_dir: str = "data"


settings = Settings()
