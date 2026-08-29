"""
MediRAG AI – Application Configuration
Pydantic v2 compatible settings management.
"""

from functools import lru_cache
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="MediRAG AI", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")
    environment: str = Field(default="production", alias="ENVIRONMENT")

    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    # Security
    secret_key: str = Field(
        default="change-this-secret-key-in-production-32chars!!",
        alias="SECRET_KEY",
    )
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./medirag.db",
        alias="DATABASE_URL",
    )

    # Ollama / LLM
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    llm_model: str = Field(default="llama3-8b-8192", alias="LLM_MODEL")
    llm_temperature: float = Field(default=0.1, alias="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=2048, alias="LLM_MAX_TOKENS")

    # Groq
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")

    # Embeddings
    embedding_model: str = Field(default="BAAI/bge-small-en-v1.5", alias="EMBEDDING_MODEL")
    embedding_device: str = Field(default="cpu", alias="EMBEDDING_DEVICE")

    # Vector Store
    vector_store_type: str = Field(default="chroma", alias="VECTOR_STORE_TYPE")
    chroma_persist_directory: str = Field(
        default="../data/embeddings/vector_store/chroma_db",
        alias="CHROMA_PERSIST_DIRECTORY",
    )
    faiss_index_path: str = Field(
        default="../data/embeddings/vector_store/faiss_index",
        alias="FAISS_INDEX_PATH",
    )

    # Document Storage
    upload_base_dir: str = Field(default="../data/uploaded_documents", alias="UPLOAD_BASE_DIR")
    metadata_dir: str = Field(default="../data/metadata", alias="METADATA_DIR")
    max_file_size_mb: int = Field(default=50, alias="MAX_FILE_SIZE_MB")

    # RAG
    chunk_size: int = Field(default=1000, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, alias="CHUNK_OVERLAP")
    top_k_results: int = Field(default=5, alias="TOP_K_RESULTS")

    # Rate Limiting
    rate_limit_requests: int = Field(default=100, alias="RATE_LIMIT_REQUESTS")
    rate_limit_period: int = Field(default=60, alias="RATE_LIMIT_PERIOD")

    # CORS
    allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:3001",
        alias="ALLOWED_ORIGINS",
    )

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    allowed_mime_types: List[str] = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "application/msword",
    ]

    document_categories: List[str] = [
        "medical_pdfs",
        "treatment_guidelines",
        "drug_databases",
        "research_articles",
        "medical_books",
        "clinical_protocols",
    ]


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
