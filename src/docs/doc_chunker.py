"""
Document Chunker - Split documentation into searchable semantic chunks

This module provides functionality to split large documentation files
into smaller, semantically meaningful chunks for better retrieval.
"""

import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class DocChunk:
    """Represents a chunk of documentation."""
    class_name: str
    section_title: str
    content: str
    chunk_type: str  # "description", "constructor", "method", "example", "topic"
    method_name: Optional[str] = None
    start_pos: int = 0
    end_pos: int = 0


@dataclass  
class CodeExample:
    """Represents a code example extracted from documentation."""
    title: str
    code: str
    language: str
    context: str


class DocChunker:
    """
    Splits documentation into semantic chunks for better retrieval.
    
    Chunks are organized by:
    - Class description
    - Individual methods
    - Code examples
    - Sections (for topic documents)
    """
    
    def __init__(self, max_chunk_size: int = 2000):
        """
        Initialize the DocChunker.
        
        Args:
            max_chunk_size: Maximum size of a single chunk in characters
        """
        self.max_chunk_size = max_chunk_size
    
    def chunk_class_doc(self, content: str, class_name: str) -> List[DocChunk]:
        """
        Split a class documentation into chunks.
        
        Args:
            content: Full markdown content of the class
            class_name: Name of the class
            
        Returns:
            List of DocChunk objects
        """
        chunks: List[DocChunk] = []
        
        # Extract class description (everything before ## sections)
        desc_match = re.search(r'^(.*?)(?=##\s)', content, re.DOTALL)
        if desc_match:
            description = desc_match.group(1).strip()
            if description:
                chunks.append(DocChunk(
                    class_name=class_name,
                    section_title="Class Description",
                    content=description[:self.max_chunk_size],
                    chunk_type="description",
                    start_pos=0,
                    end_pos=len(description)
                ))
        
        # Extract method documentation from Detailed description
        detail_match = re.search(r'##\s*Detailed description(.*?)$', content, re.DOTALL | re.IGNORECASE)
        if detail_match:
            detail_content = detail_match.group(1)
            method_chunks = self._extract_method_chunks(detail_content, class_name)
            chunks.extend(method_chunks)
        
        # Extract any code examples
        examples = self.extract_examples(content)
        for i, example in enumerate(examples):
            chunks.append(DocChunk(
                class_name=class_name,
                section_title=example.title or f"Example {i+1}",
                content=f"```{example.language}\n{example.code}\n```\n\n{example.context}",
                chunk_type="example"
            ))
        
        return chunks
    
    def _extract_method_chunks(self, content: str, class_name: str) -> List[DocChunk]:
        """Extract method documentation as individual chunks."""
        chunks: List[DocChunk] = []
        
        # Split by method headers (### method_name)
        method_blocks = re.split(r'(###\s+[^\n]+)', content)
        
        current_method = None
        current_content = []
        
        for block in method_blocks:
            if block.startswith('###'):
                # Save previous method
                if current_method and current_content:
                    full_content = '\n'.join(current_content)
                    chunks.append(DocChunk(
                        class_name=class_name,
                        section_title=current_method,
                        content=full_content[:self.max_chunk_size],
                        chunk_type="method",
                        method_name=current_method.replace('### ', '')
                    ))
                
                # Start new method
                current_method = block.strip()
                current_content = [block]
            else:
                if current_method:
                    current_content.append(block)
        
        # Don't forget the last method
        if current_method and current_content:
            full_content = '\n'.join(current_content)
            chunks.append(DocChunk(
                class_name=class_name,
                section_title=current_method,
                content=full_content[:self.max_chunk_size],
                chunk_type="method",
                method_name=current_method.replace('### ', '')
            ))
        
        return chunks
    
    def chunk_topic_doc(self, content: str, topic_name: str) -> List[DocChunk]:
        """
        Split a topic documentation into chunks.
        
        Args:
            content: Full markdown content
            topic_name: Name of the topic
            
        Returns:
            List of DocChunk objects
        """
        chunks: List[DocChunk] = []
        
        # Split by ## headers
        sections = re.split(r'(##\s+[^\n]+)', content)
        
        current_section = "Introduction"
        current_content = []
        
        for section in sections:
            if section.startswith('##') and not section.startswith('###'):
                # Save previous section
                if current_content:
                    full_content = '\n'.join(current_content)
                    if full_content.strip():
                        chunks.append(DocChunk(
                            class_name=topic_name,
                            section_title=current_section,
                            content=full_content[:self.max_chunk_size],
                            chunk_type="topic"
                        ))
                
                # Start new section
                current_section = section.replace('##', '').strip()
                current_content = [section]
            else:
                current_content.append(section)
        
        # Don't forget the last section
        if current_content:
            full_content = '\n'.join(current_content)
            if full_content.strip():
                chunks.append(DocChunk(
                    class_name=topic_name,
                    section_title=current_section,
                    content=full_content[:self.max_chunk_size],
                    chunk_type="topic"
                ))
        
        return chunks
    
    def chunk_by_section(self, content: str, class_name: str = "") -> List[DocChunk]:
        """
        Split document by markdown section headers.
        
        Args:
            content: Markdown content
            class_name: Optional class name for context
            
        Returns:
            List of DocChunk objects
        """
        chunks: List[DocChunk] = []
        
        # Find all ## headers and split
        pattern = r'(##\s+[^\n]+)'
        parts = re.split(pattern, content)
        
        current_title = "Introduction"
        current_content = ""
        
        for part in parts:
            if re.match(r'##\s+', part):
                # Save previous chunk
                if current_content.strip():
                    chunks.append(DocChunk(
                        class_name=class_name,
                        section_title=current_title,
                        content=current_content[:self.max_chunk_size],
                        chunk_type="section"
                    ))
                current_title = part.replace('##', '').strip()
                current_content = part + "\n"
            else:
                current_content += part
        
        # Add last chunk
        if current_content.strip():
            chunks.append(DocChunk(
                class_name=class_name,
                section_title=current_title,
                content=current_content[:self.max_chunk_size],
                chunk_type="section"
            ))
        
        return chunks
    
    def extract_examples(self, content: str) -> List[CodeExample]:
        """
        Extract code examples from documentation.
        
        Args:
            content: Markdown content
            
        Returns:
            List of CodeExample objects
        """
        examples: List[CodeExample] = []
        
        # Find code blocks with optional language specifier
        # Pattern: ```language\ncode\n```
        pattern = r'```(\w*)\n(.*?)```'
        matches = re.finditer(pattern, content, re.DOTALL)
        
        for match in matches:
            language = match.group(1) or "ruby"  # Default to ruby for KLayout
            code = match.group(2).strip()
            
            # Get surrounding context (text before the code block)
            start = match.start()
            context_start = max(0, start - 200)
            context = content[context_start:start].strip()
            
            # Extract title from context if possible
            title_match = re.search(r'###?\s+([^\n]+)', context)
            title = title_match.group(1) if title_match else ""
            
            examples.append(CodeExample(
                title=title,
                code=code,
                language=language,
                context=context[-100:] if len(context) > 100 else context
            ))
        
        return examples
    
    def get_method_chunk(self, content: str, class_name: str, 
                         method_name: str) -> Optional[DocChunk]:
        """
        Get a specific method's documentation as a chunk.
        
        Args:
            content: Full class documentation
            class_name: Name of the class
            method_name: Name of the method
            
        Returns:
            DocChunk for the method or None if not found
        """
        # Find method in Detailed description
        pattern = rf'###\s+{re.escape(method_name)}\s*(.*?)(?=###\s+\w|$)'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            method_content = f"### {method_name}\n{match.group(1).strip()}"
            return DocChunk(
                class_name=class_name,
                section_title=f"Method: {method_name}",
                content=method_content[:self.max_chunk_size],
                chunk_type="method",
                method_name=method_name
            )
        
        return None
    
    def get_context_window(self, chunks: List[DocChunk], 
                           target_chunk: DocChunk,
                           window_size: int = 1) -> List[DocChunk]:
        """
        Get surrounding chunks for context.
        
        Args:
            chunks: List of all chunks
            target_chunk: The chunk to get context for
            window_size: Number of chunks before/after to include
            
        Returns:
            List of chunks including target and surrounding context
        """
        try:
            idx = chunks.index(target_chunk)
        except ValueError:
            return [target_chunk]
        
        start = max(0, idx - window_size)
        end = min(len(chunks), idx + window_size + 1)
        
        return chunks[start:end]
