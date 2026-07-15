from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import cache
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent.parent / ".env",
    )

    api_key: SecretStr
    llm_model: str
    llm_base_url: str
    llm_provider: str


@cache
def get_settings() -> Settings:
    return Settings()



if __name__ == "__main__":
    print(get_settings())