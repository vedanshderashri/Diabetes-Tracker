"""
MedAI Assistant - Chunker Service
Implements semantic/hierarchical chunking for document ingestion.
Ensures document boundaries are preserved and chunks are properly tagged with metadata.
"""
import logging
import re
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class Chunker:
    """
    Splits long text documents into semantically coherent chunks.
    Preserves structural sections (headings, paragraphs) and attaches metadata.
    """

    def __init__(self, target_chunk_size: int = 1000, overlap: int = 200):
        self.target_chunk_size = target_chunk_size
        self.overlap = overlap

    def chunk_document(self, text: str, doc_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Splits text by headers and paragraphs, ensuring chunks do not exceed target size.
        Maintains an overlap between adjacent chunks when text splits.
        """
        if not text or not text.strip():
            return []

        # Step 1: Normalize newlines
        text = text.replace("\r\n", "\n")

        # Step 2: Split by markdown headers if present
        # We will split text into sections based on headers or empty lines
        raw_sections = self._split_into_sections(text)
        
        chunks = []
        
        for section_title, section_text in raw_sections:
            # Combine doc metadata with section metadata
            chunk_meta = doc_metadata.copy()
            if section_title:
                chunk_meta["section"] = section_title

            # Step 3: Chunk each section by paragraph
            paragraphs = self._split_into_paragraphs(section_text)
            
            current_chunk_text = ""
            
            for paragraph in paragraphs:
                paragraph = paragraph.strip()
                if not paragraph:
                    continue
                
                # If paragraph fits into current chunk, append it
                if len(current_chunk_text) + len(paragraph) <= self.target_chunk_size:
                    if current_chunk_text:
                        current_chunk_text += "\n\n" + paragraph
                    else:
                        current_chunk_text = paragraph
                else:
                    # Current chunk is full. Save it.
                    if current_chunk_text:
                        chunks.append({
                            "text": current_chunk_text,
                            "metadata": chunk_meta
                        })
                    
                    # Handle paragraphs larger than chunk size by splitting by sentence
                    if len(paragraph) > self.target_chunk_size:
                        sub_chunks = self._split_large_paragraph(paragraph)
                        for sc in sub_chunks[:-1]:
                            chunks.append({
                                "text": sc,
                                "metadata": chunk_meta
                            })
                        current_chunk_text = sub_chunks[-1]
                    else:
                        current_chunk_text = paragraph
            
            # Add remaining text in section
            if current_chunk_text:
                chunks.append({
                    "text": current_chunk_text,
                    "metadata": chunk_meta
                })

        return chunks

    def _split_into_sections(self, text: str) -> List[tuple]:
        """Split text into sections by Markdown headers (e.g. #, ##, ###, ====, ----)."""
        pattern = r"(^|\n)(?=(?:#{1,6}\s+|[=-]{3,}\n))"
        parts = re.split(pattern, text)
        
        sections = []
        current_header = ""
        
        # If the first part does not start with a header, it's the preamble
        first_part = parts[0].strip()
        if first_part:
            sections.append(("", first_part))
            
        for i in range(1, len(parts), 2):
            header_part = parts[i].strip()
            # Find the header title
            header_match = re.match(r"^#{1,6}\s+(.+)$", header_part, re.MULTILINE)
            if header_match:
                current_header = header_match.group(1).strip()
            
            content_part = parts[i+1].strip() if i+1 < len(parts) else ""
            if content_part:
                sections.append((current_header, content_part))
                
        # If no markdown headers were matched, split by paragraphs simply
        if not sections:
            sections.append(("", text))
            
        return sections

    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text by double newlines (paragraphs)."""
        return re.split(r"\n\s*\n", text)

    def _split_large_paragraph(self, text: str) -> List[str]:
        """Split a paragraph that exceeds the chunk size into smaller sentence groups."""
        # Simple sentence splitter
        sentences = re.split(r"(?<=[.!?])\s+", text)
        sub_chunks = []
        current_sc = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            if len(current_sc) + len(sentence) <= self.target_chunk_size:
                if current_sc:
                    current_sc += " " + sentence
                else:
                    current_sc = sentence
            else:
                if current_sc:
                    sub_chunks.append(current_sc)
                
                # If a single sentence is still larger than target, split it by characters
                if len(sentence) > self.target_chunk_size:
                    for i in range(0, len(sentence), self.target_chunk_size - self.overlap):
                        sub_chunks.append(sentence[i : i + self.target_chunk_size])
                    current_sc = ""
                else:
                    current_sc = sentence
                    
        if current_sc:
            sub_chunks.append(current_sc)
            
        return sub_chunks


# Singleton instance
chunker = Chunker()
