from typing import List, Optional, Any

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Search request model."""

    query: str = Field(..., min_length=1, max_length=500, description="Search query across title, abstract, and authors")
    size: int = Field(default=10, ge=1, le=50, description="Number of results to return")
    from_: int = Field(default=0, ge=0, alias="from", description="Offset for pagination")
    tags: Optional[List[str]] = Field(default=None, description="Filter by tags")
    sort_by_date: bool = Field(default=False, description="Sort by publication date (newest first) instead of relevance")


class HybridSearchRequest(BaseModel):
    """Request model for hybrid search supporting all search modes."""

    query: str = Field(..., description="Search query text", min_length=1, max_length=500)
    size: int = Field(10, description="Number of results to return", ge=1, le=100)
    from_: int = Field(0, description="Offset for pagination", ge=0, alias="from")
    tags: Optional[List[str]] = Field(None, description="Filter by document tags (e.g., ['machine learning', 'natural language processing'])")
    sort_by_date: bool = Field(False, description="Sort by publication date instead of relevance")
    use_hybrid: bool = Field(True, description="Enable hybrid search (BM25 + vector) with automatic embedding generation")
    min_score: float = Field(0.0, description="Minimum score threshold for results", ge=0.0)
    
    # Advanced Enterprise filters
    document_type: Optional[str] = Field(None, description="Filter by document classification category")
    department: Optional[str] = Field(None, description="Filter by corporate department")
    access_level: Optional[str] = Field(None, description="Filter by document security level")
    notice_period_days: Optional[int] = Field(None, description="Filter by termination notice period (exact match in days)")
    min_liability_cap: Optional[float] = Field(None, description="Filter by minimum liability cap limit")
    
    # Backward compatibility fields
    categories: Optional[List[str]] = Field(None, description="Filter by categories list")
    latest_papers: bool = Field(False, description="Sort and limit by latest paper publications")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "query": "enterprise knowledge management",
                "size": 10,
                "tags": ["internal docs", "HR policy"],
                "sort_by_date": False,
                "use_hybrid": True,
            }
        }


class SearchHit(BaseModel):
    """Individual search result."""

    external_id: Optional[str] = None  # External ID from original source
    arxiv_id: Optional[str] = None
    title: str
    contributors: Optional[Any] = None
    authors: Optional[Any] = None
    abstract: Optional[str] = None
    source_created_at: Optional[str] = None
    created_at: Optional[str] = None
    source_url: Optional[str] = None
    pdf_url: Optional[str] = None
    source_type: Optional[str] = None
    score: float
    highlights: Optional[dict] = None

    # Chunk-specific fields (for unified search)
    chunk_text: Optional[str] = Field(None, description="Text content of the matching chunk")
    chunk_id: Optional[str] = Field(None, description="Unique identifier of the chunk")
    section_name: Optional[str] = Field(None, description="Section name where the chunk was found")
    document_type: Optional[str] = None
    access_level: Optional[str] = None
    compliance_report: Optional[dict] = None


class SearchResponse(BaseModel):
    """Search response model."""

    query: str
    total: int
    hits: List[SearchHit]
    size: int = Field(description="Number of results requested")
    from_: int = Field(alias="from", description="Offset used for pagination")
    search_mode: Optional[str] = Field(None, description="Search mode used: bm25, vector, or hybrid")
    error: Optional[str] = None

    class Config:
        populate_by_name = True
