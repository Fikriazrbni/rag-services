"""Text chunking engine with configurable chunk size and overlap."""

from dataclasses import dataclass
from typing import Optional

import tiktoken

from app.utils.file_parser import PageContent


@dataclass
class ChunkData:
    content: str
    page_number: Optional[int]
    paragraph_position: int
    character_offset: int


class TextChunker:
    """Splits text into overlapping chunks using token-based splitting."""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        model_name: str = "cl100k_base",
    ):
        # Validate configuration
        if chunk_size < 64 or chunk_size > 4096:
            raise ValueError(
                f"chunk_size must be between 64 and 4096, got {chunk_size}"
            )
        if chunk_overlap < 0:
            raise ValueError(
                f"chunk_overlap must be >= 0, got {chunk_overlap}"
            )
        if chunk_overlap >= chunk_size:
            raise ValueError(
                f"chunk_overlap ({chunk_overlap}) must be less than chunk_size ({chunk_size})"
            )

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.tokenizer = tiktoken.get_encoding(model_name)

    def chunk_pages(self, pages: list[PageContent]) -> list[ChunkData]:
        """Chunk a list of pages into ChunkData objects."""
        all_chunks: list[ChunkData] = []
        chunk_position = 0

        for page in pages:
            page_chunks = self._chunk_text(
                text=page.text,
                page_number=page.page_number,
                start_position=chunk_position,
            )
            all_chunks.extend(page_chunks)
            chunk_position += len(page_chunks)

        return all_chunks

    def _chunk_text(
        self,
        text: str,
        page_number: Optional[int],
        start_position: int = 0,
    ) -> list[ChunkData]:
        """Split text into overlapping chunks by token count."""
        tokens = self.tokenizer.encode(text)

        if len(tokens) <= self.chunk_size:
            return [
                ChunkData(
                    content=text,
                    page_number=page_number,
                    paragraph_position=start_position,
                    character_offset=0,
                )
            ]

        chunks: list[ChunkData] = []
        start_token = 0
        position = start_position

        while start_token < len(tokens):
            end_token = min(start_token + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start_token:end_token]
            chunk_text = self.tokenizer.decode(chunk_tokens)

            # Calculate character offset in original text
            prefix_tokens = tokens[:start_token]
            char_offset = len(self.tokenizer.decode(prefix_tokens))

            chunks.append(
                ChunkData(
                    content=chunk_text,
                    page_number=page_number,
                    paragraph_position=position,
                    character_offset=char_offset,
                )
            )

            position += 1
            start_token += self.chunk_size - self.chunk_overlap

            # Prevent infinite loop
            if start_token >= len(tokens):
                break

        return chunks
