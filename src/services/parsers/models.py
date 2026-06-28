from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from src.schemas.pdf_parser.models import ParserType


class ParsedDocument(BaseModel):
    """Result of parsing an uploaded document."""

    filename: str
    pages: int = 1
    content: str
    file_size_bytes: int
    parser_used: ParserType
    metadata: Dict[str, Any] = Field(default_factory=dict)
    page_texts: Optional[list[str]] = None
