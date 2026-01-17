"""
Text chunking service for enterprise documents.
Uses hybrid section-aware strategy: section-based when available, falls back to word-based chunking.
Preserves 600 word chunks with 100 word overlap from original arXiv implementation.
"""

import json
import logging
import re
from typing import Dict, List, Optional, Union

from src.schemas.indexing.models import ChunkMetadata, TextChunk

logger = logging.getLogger(__name__)


class TextChunker:
    """
    Service for chunking enterprise documents into overlapping segments.
    
    Strategy:
    - For sections 100-800 words: Use as single chunk with enterprise context header
    - For sections <100 words: Combine with adjacent sections
    - For sections >800 words: Split using traditional word-based chunking
    - Fallback to traditional chunking if no sections available
    
    Default: 600 words per chunk with 100 word overlap.
    """
    
    def __init__(self, chunk_size: int = 600, overlap_size: int = 100, min_chunk_size: int = 100):
        """
        Initialize text chunker.
        
        :param chunk_size: Target number of words per chunk
        :param overlap_size: Number of overlapping words between chunks
        :param min_chunk_size: Minimum words for a chunk to be valid
        """
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
        self.min_chunk_size = min_chunk_size
        
        if overlap_size >= chunk_size:
            raise ValueError("Overlap size must be less than chunk size")
        
        logger.info(
            f"Text chunker initialized: chunk_size={chunk_size}, "
            f"overlap_size={overlap_size}, min_chunk_size={min_chunk_size}"
        )
    
    def _split_into_words(self, text: str) -> List[str]:
        """
        Split text into words while preserving whitespace information.
        
        :param text: Input text
        :returns: List of words
        """
        # Split on whitespace while keeping the words
        words = re.findall(r"\S+", text)
        return words
    
    def _reconstruct_text(self, words: List[str]) -> str:
        """
        Reconstruct text from words.
        
        :param words: List of words
        :returns: Reconstructed text
        """
        return " ".join(words)
    
    def chunk_document(
        self,
        title: str,
        full_text: str,
        document_id: str,
        version_id: str,
        sections: Optional[Union[Dict[str, str], str, list]] = None,
        department: Optional[str] = None,
        document_type: Optional[str] = None,
    ) -> List[TextChunk]:
        """
        Chunk an enterprise document using hybrid section-based approach.
        
        Adds enterprise context header (department, document_type) to each chunk
        for better retrieval and access control context.
        
        Strategy:
        - For sections 100-800 words: Use as single chunk with context header
        - For sections <100 words: Combine with adjacent sections
        - For sections >800 words: Split using traditional word-based chunking
        - Fallback to traditional chunking if no sections available
        
        :param title: Document title
        :param full_text: Full text content
        :param document_id: Enterprise document ID
        :param version_id: Document version ID
        :param sections: Document sections (dict, JSON string, or list)
        :param department: Document department for context
        :param document_type: Document type for context
        :returns: List of text chunks with metadata
        """
        # Add enterprise context header
        context_header = f"Document: {title}\n"
        if department:
            context_header += f"Department: {department}\n"
        if document_type:
            context_header += f"Type: {document_type}\n"
        context_header += "\n"
        
        # Try section-based chunking first
        if sections:
            try:
                section_chunks = self._chunk_by_sections(
                    context_header, document_id, version_id, sections
                )
                if section_chunks:
                    logger.info(f"Created {len(section_chunks)} section-based chunks for {document_id}")
                    return section_chunks
            except Exception as e:
                logger.warning(f"Section-based chunking failed for {document_id}: {e}")
        
        # Fallback to traditional word-based chunking
        logger.info(f"Using traditional word-based chunking for document {document_id}")
        return self.chunk_text(context_header + full_text, document_id, version_id)
    
    def chunk_text(self, text: str, document_id: str, version_id: str) -> List[TextChunk]:
        """
        Chunk text into overlapping segments using word-based approach.
        
        :param text: Full text to chunk (including context header)
        :param document_id: Document ID
        :param version_id: Version ID
        :returns: List of text chunks with metadata
        """
        if not text or not text.strip():
            logger.warning(f"Empty text provided for document {document_id}")
            return []
        
        # Split text into words
        words = self._split_into_words(text)
        
        if len(words) < self.min_chunk_size:
            logger.warning(
                f"Text for document {document_id} has only {len(words)} words, "
                f"less than minimum {self.min_chunk_size}"
            )
            # Return single chunk if text is too small
            if words:
                return [
                    TextChunk(
                        text=self._reconstruct_text(words),
                        metadata=ChunkMetadata(
                            chunk_index=0,
                            start_char=0,
                            end_char=len(text),
                            word_count=len(words),
                            overlap_with_previous=0,
                            overlap_with_next=0,
                            section_title="Full Document",
                        ),
                        arxiv_id=document_id,  # Keep for compatibility
                        paper_id=version_id,
                    )
                ]
            return []
        
        chunks = []
        chunk_index = 0
        current_position = 0
        
        while current_position < len(words):
            # Calculate chunk boundaries
            chunk_start = current_position
            chunk_end = min(current_position + self.chunk_size, len(words))
            
            # Extract chunk words
            chunk_words = words[chunk_start:chunk_end]
            chunk_text = self._reconstruct_text(chunk_words)
            
            # Calculate character offsets (approximate)
            start_char = len(" ".join(words[:chunk_start])) if chunk_start > 0 else 0
            end_char = len(" ".join(words[:chunk_end]))
            
            # Calculate overlaps
            overlap_with_previous = min(self.overlap_size, chunk_start) if chunk_start > 0 else 0
            overlap_with_next = self.overlap_size if chunk_end < len(words) else 0
            
            # Create chunk
            chunk = TextChunk(
                text=chunk_text,
                metadata=ChunkMetadata(
                    chunk_index=chunk_index,
                    start_char=start_char,
                    end_char=end_char,
                    word_count=len(chunk_words),
                    overlap_with_previous=overlap_with_previous,
                    overlap_with_next=overlap_with_next,
                    section_title=f"Part {chunk_index + 1}",  # Generic section title for word-based chunks
                ),
                arxiv_id=document_id,  # Keep for compatibility
                paper_id=version_id,
            )
            chunks.append(chunk)
            
            # Move to next chunk position (with overlap)
            current_position += self.chunk_size - self.overlap_size
            chunk_index += 1
            
            # Break if we've processed all words
            if chunk_end >= len(words):
                break
        
        logger.info(
            f"Chunked document {document_id}: {len(words)} words -> {len(chunks)} chunks"
        )
        return chunks
    
    def _chunk_by_sections(
        self,
        context_header: str,
        document_id: str,
        version_id: str,
        sections: Union[Dict[str, str], str, list],
    ) -> List[TextChunk]:
        """
        Implement hybrid section-based chunking strategy for enterprise documents.
        
        :param context_header: Header with enterprise context (department, type)
        :param document_id: Document ID
        :param version_id: Version ID
        :param sections: Sections data (dict, JSON string, or list)
        :returns: List of text chunks
        """
        # Parse sections data
        sections_dict = self._parse_sections(sections)
        if not sections_dict:
            return []
        
        # Filter sections (remove empty ones)
        sections_dict = self._filter_sections(sections_dict)
        if not sections_dict:
            logger.warning(f"No meaningful sections found after filtering for document {document_id}")
            return []
        
        # Process sections using hybrid strategy
        chunks = []
        small_sections = []  # Buffer for combining small sections
        
        section_items = list(sections_dict.items())
        
        for i, (section_title, section_content) in enumerate(section_items):
            content_str = str(section_content) if section_content else ""
            section_words = len(content_str.split())
            
            if section_words < 100:
                # Collect small sections to combine later
                small_sections.append((section_title, content_str, section_words))
                
                # If this is the last section or next section is large, process accumulated small sections
                if i == len(section_items) - 1 or len(str(section_items[i + 1][1]).split()) >= 100:
                    chunks.extend(
                        self._create_combined_chunk(
                            context_header, small_sections, chunks, document_id, version_id
                        )
                    )
                    small_sections = []
            
            elif 100 <= section_words <= 800:
                # Perfect size - create single chunk
                chunk_text = f"{context_header}Section: {section_title}\n\n{content_str}"
                chunk = self._create_section_chunk(
                    chunk_text, section_title, len(chunks), document_id, version_id
                )
                chunks.append(chunk)
            
            else:
                # Large section - split using traditional chunking
                section_text = f"Section: {section_title}\n\n{content_str}"
                full_section_text = f"{context_header}{section_text}"
                
                # Use traditional chunking but with section context
                section_chunks = self._split_large_section(
                    full_section_text,
                    context_header,
                    section_title,
                    len(chunks),
                    document_id,
                    version_id,
                )
                chunks.extend(section_chunks)
        
        return chunks
    
    def _parse_sections(self, sections: Union[Dict[str, str], str, list]) -> Dict[str, str]:
        """
        Parse sections data into a dictionary.
        """
        if isinstance(sections, dict):
            return sections
        elif isinstance(sections, list):
            # Handle list of sections directly
            result = {}
            for i, section in enumerate(sections):
                if isinstance(section, dict):
                    title = section.get("title", section.get("heading", f"Section {i + 1}"))
                    content = section.get("content", section.get("text", ""))
                    result[title] = content
                else:
                    result[f"Section {i + 1}"] = str(section)
            return result
        elif isinstance(sections, str):
            try:
                parsed = json.loads(sections)
                if isinstance(parsed, dict):
                    return parsed
                elif isinstance(parsed, list):
                    # Convert list to dict with enumerated keys
                    result = {}
                    for i, section in enumerate(parsed):
                        if isinstance(section, dict):
                            title = section.get("title", section.get("heading", f"Section {i + 1}"))
                            content = section.get("content", section.get("text", ""))
                            result[title] = content
                        else:
                            result[f"Section {i + 1}"] = str(section)
                    return result
            except json.JSONDecodeError:
                logger.warning("Failed to parse sections JSON string")
        return {}
    
    def _filter_sections(self, sections_dict: Dict[str, str]) -> Dict[str, str]:
        """
        Filter out empty or unwanted sections.
        
        :param sections_dict: Dictionary of sections
        :returns: Filtered dictionary
        """
        filtered = {}
        
        for section_title, section_content in sections_dict.items():
            content_str = str(section_content).strip()
            
            # Skip empty sections
            if not content_str:
                continue
            
            # Skip sections that are too small and contain only metadata
            if len(content_str.split()) < 20 and self._is_metadata_content(content_str):
                logger.debug(f"Skipping metadata section: {section_title}")
                continue
            
            filtered[section_title] = content_str
        
        return filtered
    
    def _is_metadata_content(self, content: str) -> bool:
        """
        Check if content contains only metadata (emails, IDs, etc.).
        """
        content_lower = content.lower()
        
        # Check for common metadata patterns
        metadata_patterns = [
            "@",  # Email addresses
            "document id:",
            "version:",
            "author:",
            "created:",
            "modified:",
            "confidential",
        ]
        
        # If content is short and contains metadata patterns
        word_count = len(content.split())
        if word_count < 30:
            pattern_count = sum(1 for pattern in metadata_patterns if pattern in content_lower)
            if pattern_count >= 2:
                return True
        
        return False
    
    def _create_combined_chunk(
        self,
        context_header: str,
        small_sections: List,
        existing_chunks: List,
        document_id: str,
        version_id: str,
    ) -> List[TextChunk]:
        """
        Create chunks by combining small sections.
        """
        if not small_sections:
            return []
        
        # Combine all small sections
        combined_content = []
        total_words = 0
        
        for section_title, content, word_count in small_sections:
            combined_content.append(f"Section: {section_title}\n\n{content}")
            total_words += word_count
        
        combined_text = f"{context_header}{'\n\n'.join(combined_content)}"
        
        # If still too small, combine with previous chunk if possible
        if total_words + len(context_header.split()) < 200 and existing_chunks:
            # Try to merge with previous chunk
            prev_chunk = existing_chunks[-1]
            merged_text = f"{prev_chunk.text}\n\n{'\n\n'.join(combined_content)}"
            
            # Update the previous chunk
            existing_chunks[-1] = TextChunk(
                text=merged_text,
                metadata=ChunkMetadata(
                    chunk_index=prev_chunk.metadata.chunk_index,
                    start_char=0,
                    end_char=len(merged_text),
                    word_count=len(merged_text.split()),
                    overlap_with_previous=0,
                    overlap_with_next=0,
                    section_title=f"{prev_chunk.metadata.section_title} + Combined",
                ),
                arxiv_id=document_id,
                paper_id=version_id,
            )
            return []
        
        # Create new chunk with combined content
        sections_titles = [title for title, _, _ in small_sections]
        combined_title = " + ".join(sections_titles[:3])  # Limit title length
        if len(sections_titles) > 3:
            combined_title += f" + {len(sections_titles) - 3} more"
        
        chunk = self._create_section_chunk(
            combined_text, combined_title, len(existing_chunks), document_id, version_id
        )
        return [chunk]
    
    def _create_section_chunk(
        self, chunk_text: str, section_title: str, chunk_index: int, document_id: str, version_id: str
    ) -> TextChunk:
        """
        Create a single section-based chunk.
        """
        return TextChunk(
            text=chunk_text,
            metadata=ChunkMetadata(
                chunk_index=chunk_index,
                start_char=0,
                end_char=len(chunk_text),
                word_count=len(chunk_text.split()),
                overlap_with_previous=0,
                overlap_with_next=0,
                section_title=section_title,
            ),
            arxiv_id=document_id,  # Keep for compatibility
            paper_id=version_id,
        )
    
    def _split_large_section(
        self,
        full_section_text: str,
        context_header: str,
        section_title: str,
        base_chunk_index: int,
        document_id: str,
        version_id: str,
    ) -> List[TextChunk]:
        """
        Split large sections using traditional word-based chunking.
        """
        # Remove header from section text for chunking, then add back to each chunk
        header_length = len(context_header)
        section_only = full_section_text[header_length:]
        
        # Use traditional chunking on section content
        traditional_chunks = self.chunk_text(section_only, document_id, version_id)
        
        # Add header to each chunk and update metadata
        enhanced_chunks = []
        for i, chunk in enumerate(traditional_chunks):
            enhanced_text = f"{context_header}{chunk.text}"
            
            enhanced_chunk = TextChunk(
                text=enhanced_text,
                metadata=ChunkMetadata(
                    chunk_index=base_chunk_index + i,
                    start_char=chunk.metadata.start_char,
                    end_char=chunk.metadata.end_char + header_length,
                    word_count=len(enhanced_text.split()),
                    overlap_with_previous=chunk.metadata.overlap_with_previous,
                    overlap_with_next=chunk.metadata.overlap_with_next,
                    section_title=f"{section_title} (Part {i + 1})",
                ),
                arxiv_id=document_id,
                paper_id=version_id,
            )
            enhanced_chunks.append(enhanced_chunk)
        
        return enhanced_chunks
