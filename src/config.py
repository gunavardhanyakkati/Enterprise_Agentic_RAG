import os
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE_PATH = PROJECT_ROOT / ".env"


class BaseConfigSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        extra="ignore",
        frozen=True,
        env_nested_delimiter="__",
        case_sensitive=False,
    )


class PDFParserSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="PDF_PARSER__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    max_pages: int = 30
    max_file_size_mb: int = 20
    do_ocr: bool = False
    do_table_structure: bool = True


class EnterpriseSourceSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="ENTERPRISE_SOURCE__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    source_type: Literal["s3", "filesystem", "sharepoint"] = "filesystem"
    s3_bucket: str = ""
    s3_prefix: str = "documents/"
    s3_region: str = "us-east-1"
    filesystem_path: str = "./data/enterprise_documents"


class SecuritySettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="SECURITY__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    jwt_secret: str = "change-me-in-production-at-least-32-characters"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24
    ldap_server: str = ""
    ldap_base_dn: str = ""
    default_access_level: Literal["public", "internal", "confidential", "restricted"] = "internal"
    rbac_enabled: bool = True
    admin_roles: List[str] = Field(default_factory=lambda: ["admin", "superuser"])


class DocumentLifecycleSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="DOCUMENT_LIFECYCLE__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    retention_days: int = 2555  # 7 years default
    max_versions: int = 10
    auto_archive_days: int = 365
    virus_scan_enabled: bool = False
    pii_scan_enabled: bool = False


class ChunkingSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="CHUNKING__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    chunk_size: int = 1000
    overlap_size: int = 200
    min_chunk_size: int = 50
    section_based: bool = False


class EmbeddingsSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="EMBEDDINGS__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    provider: Literal["local", "jina"] = "local"
    local_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    local_dimension: int = 384


class GeminiSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="GEMINI__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    api_key: str = ""
    model: str = "gemini-2.0-flash"
    enabled: bool = True
    auto_run_on_upload: bool = True
    max_content_chars: int = 30000


class OpenSearchSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="OPENSEARCH__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    host: str = "http://localhost:9200"
    index_name: str = "enterprise-documents"
    chunk_index_suffix: str = "chunks"
    max_text_size: int = 1000000
    vector_dimension: int = 384
    vector_space_type: str = "cosinesimil"
    rrf_pipeline_name: str = "hybrid-rrf-pipeline"
    hybrid_search_size_multiplier: int = 2


class LangfuseSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="LANGFUSE__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    public_key: str = ""
    secret_key: str = ""
    host: str = "http://localhost:3000"
    enabled: bool = True
    flush_at: int = 15
    flush_interval: float = 1.0
    max_retries: int = 3
    timeout: int = 30
    debug: bool = False


class RedisSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="REDIS__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    host: str = "localhost"
    port: int = 6379
    password: str = ""
    db: int = 0
    decode_responses: bool = True
    socket_timeout: int = 30
    socket_connect_timeout: int = 30
    ttl_hours: int = 6


class TelegramSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="TELEGRAM__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    bot_token: str = ""
    enabled: bool = False


class Settings(BaseConfigSettings):
    app_version: str = "0.1.0"
    debug: bool = True
    environment: Literal["development", "staging", "production"] = "development"
    service_name: str = "enterprise-kb"

    postgres_database_url: str = "postgresql://rag_user:rag_password@localhost:5432/rag_db"
    postgres_echo_sql: bool = False
    postgres_pool_size: int = 20
    postgres_max_overflow: int = 0

    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:1b"
    ollama_timeout: int = 300

    jina_api_key: str = ""

    gemini: GeminiSettings = Field(default_factory=GeminiSettings)
    pdf_parser: PDFParserSettings = Field(default_factory=PDFParserSettings)
    enterprise_source: EnterpriseSourceSettings = Field(default_factory=EnterpriseSourceSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    document_lifecycle: DocumentLifecycleSettings = Field(default_factory=DocumentLifecycleSettings)
    chunking: ChunkingSettings = Field(default_factory=ChunkingSettings)
    embeddings: EmbeddingsSettings = Field(default_factory=EmbeddingsSettings)
    opensearch: OpenSearchSettings = Field(default_factory=OpenSearchSettings)
    langfuse: LangfuseSettings = Field(default_factory=LangfuseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)

    @field_validator("postgres_database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not (v.startswith("postgresql://") or v.startswith("postgresql+psycopg2://")):
            raise ValueError("Database URL must start with 'postgresql://' or 'postgresql+psycopg2://'")
        return v


def get_settings() -> Settings:
    return Settings()
