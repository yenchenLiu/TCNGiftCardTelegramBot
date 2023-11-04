from functools import cache

from pydantic import BaseSettings


class Settings(BaseSettings):
    db_url: str
    telegram_token: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@cache
def get_settings():
    return Settings()
