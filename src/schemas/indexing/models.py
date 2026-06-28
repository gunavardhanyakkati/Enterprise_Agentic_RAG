from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    chunk_index: int = 0
    start_char: int = 0
    end_char: int = 0
    word_count: int = 0
    overlap_with_previous: int = 0
    overlap_with_next: int = 0
    section_title: str = ""


class TextChunk(BaseModel):
    text: str
    metadata: ChunkMetadata
    arxiv_id: str = Field(description="Document identifier (legacy field name)")
    paper_id: str = Field(description="Version identifier (legacy field name)")
