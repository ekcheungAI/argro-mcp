"""Application settings, loaded from environment / .env file."""
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/argro"
    app_env: str = "dev"
    backend_port: int = 8000
    api_key: Optional[str] = None  # None = auth off

    # Embeddings / LLM
    embedding_dim: int = 1536
    llm_provider: str = "moonshot"
    moonshot_api_key: Optional[str] = None
    moonshot_base_url: str = "https://api.moonshot.ai/v1"
    embedding_model: str = "jina-embeddings-v3"  # live 實用值;DB column vector(1536),Jina 出 1024 維會 zero-pad
    embedding_base_url: Optional[str] = None  # 預設跟 moonshot_base_url;Jina 用 https://api.jina.ai/v1
    embedding_api_key: Optional[str] = None   # 預設跟 moonshot_api_key;Jina 用自己 key
    translation_model: str = "deepseek-v4-flash"  # live 實用值(OpenAI-compatible endpoint)
    target_langs: str = "en,zh-TW"

    # Ingestion
    ingestion_batch_size: int = 50
    ingestion_interval_minutes: int = 15
    worker_concurrency: int = 4

    @property
    def target_langs_list(self) -> list[str]:
        """Parse TARGET_LANGS (comma-separated) into a list of language codes."""
        return [lang.strip() for lang in self.target_langs.split(",") if lang.strip()]


settings = Settings()
