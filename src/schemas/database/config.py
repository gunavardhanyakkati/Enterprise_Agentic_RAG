from pydantic import BaseModel, Field


class PostgreSQLSettings(BaseModel):
    """PostgreSQL connection settings."""

    database_url: str = Field(..., description="SQLAlchemy database URL")
    echo_sql: bool = Field(default=False, description="Echo SQL statements")
    pool_size: int = Field(default=20, description="Connection pool size")
    max_overflow: int = Field(default=0, description="Max overflow connections")
