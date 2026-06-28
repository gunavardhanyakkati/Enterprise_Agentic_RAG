import logging

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.schemas.indexing.models import ChunkMetadata, TextChunk

logger = logging.getLogger(__name__)


class RecursiveTextChunker:
    """Character-based chunking using LangChain RecursiveCharacterTextSplitter."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
        logger.info(
            f"Recursive text chunker initialized: chunk_size={chunk_size}, overlap={chunk_overlap}"
        )

    def chunk_text(self, text: str, document_id: str, version_id: str) -> list[TextChunk]:
        if not text or not text.strip():
            logger.warning(f"Empty text provided for document {document_id}")
            return []

        splits = self.splitter.split_text(text)
        chunks: list[TextChunk] = []
        cursor = 0

        for index, split in enumerate(splits):
            start_char = text.find(split, cursor)
            if start_char == -1:
                start_char = cursor
            end_char = start_char + len(split)
            cursor = end_char

            chunks.append(
                TextChunk(
                    text=split,
                    metadata=ChunkMetadata(
                        chunk_index=index,
                        start_char=start_char,
                        end_char=end_char,
                        word_count=len(split.split()),
                        overlap_with_previous=self.chunk_overlap if index > 0 else 0,
                        overlap_with_next=self.chunk_overlap if index < len(splits) - 1 else 0,
                        section_title=f"Chunk {index + 1}",
                    ),
                    arxiv_id=document_id,
                    paper_id=version_id,
                )
            )

        logger.info(f"Chunked document {document_id}: {len(chunks)} chunks")
        return chunks
