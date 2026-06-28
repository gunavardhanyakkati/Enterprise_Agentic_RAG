from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ParserType(str, Enum):
    DOCLING = "docling"
    OFFICE = "office"
    PYMUPDF = "pymupdf"
    PYPDF = "pypdf"
    TEXT = "text"


class PaperSection(BaseModel):
    title: str
    content: str


class PaperFigure(BaseModel):
    caption: str = ""
    path: Optional[str] = None


class PaperTable(BaseModel):
    caption: str = ""
    content: str = ""


class PdfContent(BaseModel):
    sections: List[PaperSection] = Field(default_factory=list)
    figures: List[PaperFigure] = Field(default_factory=list)
    tables: List[PaperTable] = Field(default_factory=list)
    raw_text: str = ""
    references: List[str] = Field(default_factory=list)
    parser_used: ParserType = ParserType.DOCLING
    metadata: Dict[str, Any] = Field(default_factory=dict)
    page_count: Optional[int] = None
    file_size_bytes: Optional[int] = None
