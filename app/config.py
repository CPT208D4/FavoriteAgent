from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent / "data"
    )
    database_url: str | None = None
    chroma_dir: Path | None = None

    chunk_size: int = 400
    chunk_overlap: int = 80

    # 嵌入：local=本机 sentence-transformers；api=OpenAI 兼容 /v1/embeddings
    embedding_backend: Literal["local", "api"] = "local"
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    embedding_api_base: str | None = None
    embedding_api_key: str | None = None
    embedding_api_model: str | None = None
    embedding_batch_size: int = 32

    # 检索：先向量取候选再 rerank（与 top_k 配合）
    retrieve_vector_candidates: int = 24
    rerank_enabled: bool = False
    rerank_api_url: str | None = None
    rerank_api_key: str | None = None
    rerank_model: str | None = None
    rerank_timeout_seconds: int = 120

    # 问答与总结：OpenAI 兼容 /v1/chat/completions
    llm_api_base: str | None = None
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.2
    llm_timeout_seconds: int = 120

    @model_validator(mode="after")
    def _paths(self) -> "Settings":
        self.data_dir = self.data_dir.resolve()
        if self.database_url is None:
            self.database_url = f"sqlite:///{self.data_dir / 'kb.sqlite'}"
        if self.chroma_dir is None:
            self.chroma_dir = self.data_dir / "chroma"
        self.chroma_dir = self.chroma_dir.resolve()
        # LLM 未显式配置时，沿用 embedding API（便于一套 OpenAI 兼容网关）
        if not self.llm_api_base:
            self.llm_api_base = self.embedding_api_base
        if not self.llm_api_key:
            self.llm_api_key = self.embedding_api_key
        return self


settings = Settings()
