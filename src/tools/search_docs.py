"""
Search Docs Tool - Search KLayout documentation

This tool provides documentation search functionality for the MCP server.
"""

from typing import Optional, Dict, Any, List

from ..docs.document_store import DocumentStore


class SearchDocsTool:
    """
    Tool for searching KLayout documentation.
    
    Searches through general documentation and tutorials.
    """
    
    def __init__(self, doc_store: DocumentStore):
        """
        Initialize the tool.
        
        Args:
            doc_store: DocumentStore instance
        """
        self.doc_store = doc_store
    
    def search(self, query: str,
               doc_type: str = "all",
               limit: int = 5) -> Dict[str, Any]:
        """
        Search for content in documentation.
        
        Args:
            query: Search query string
            doc_type: Type of docs to search ("class", "topic", "all")
            limit: Maximum number of results
            
        Returns:
            Dictionary with search results
        """
        results = self.doc_store.search_content(query, doc_type, limit)
        
        return {
            "success": True,
            "query": query,
            "doc_type": doc_type,
            "results": [
                {
                    "name": r.class_name,
                    "type": r.section,
                    "snippet": r.snippet,
                    "score": round(r.score, 2),
                    "line": r.line_number
                }
                for r in results
            ],
            "total": len(results)
        }
    
    def get_topic(self, topic_name: str) -> Dict[str, Any]:
        """
        Get documentation for a specific topic.
        
        Args:
            topic_name: Name of the topic (e.g., "transformations", "expressions")
            
        Returns:
            Dictionary with topic documentation
        """
        doc = self.doc_store.get_topic_doc(topic_name)
        if not doc:
            return {
                "success": False,
                "error": f"Topic not found: {topic_name}"
            }
        
        return {
            "success": True,
            "topic": topic_name,
            "documentation": doc
        }
    
    def list_topics(self) -> Dict[str, Any]:
        """
        List all available topics.
        
        Returns:
            Dictionary with topic list
        """
        topics = self.doc_store.list_topics()
        return {
            "success": True,
            "topics": topics,
            "total": len(topics)
        }
    
    def search_topic(self, topic_name: str, query: str) -> Dict[str, Any]:
        """
        Search within a specific topic's documentation.
        
        Args:
            topic_name: Name of the topic
            query: Search query string
            
        Returns:
            Dictionary with search results
        """
        doc = self.doc_store.get_topic_doc(topic_name)
        if not doc:
            return {
                "success": False,
                "error": f"Topic not found: {topic_name}"
            }
        
        # Simple search within the topic
        query_lower = query.lower()
        doc_lower = doc.lower()
        
        if query_lower not in doc_lower:
            return {
                "success": True,
                "topic": topic_name,
                "query": query,
                "found": False,
                "snippets": []
            }
        
        # Find all occurrences and extract snippets
        snippets = []
        start = 0
        while True:
            pos = doc_lower.find(query_lower, start)
            if pos < 0:
                break
            
            # Extract snippet around the match
            snippet_start = max(0, pos - 50)
            snippet_end = min(len(doc), pos + len(query) + 100)
            snippet = doc[snippet_start:snippet_end].strip()
            snippets.append({
                "position": pos,
                "text": f"...{snippet}..."
            })
            
            start = pos + 1
            if len(snippets) >= 5:  # Limit snippets
                break
        
        return {
            "success": True,
            "topic": topic_name,
            "query": query,
            "found": True,
            "snippets": snippets,
            "total_matches": len(snippets)
        }
