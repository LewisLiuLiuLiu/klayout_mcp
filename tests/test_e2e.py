"""
End-to-End Tests for KLayout MCP Server

This module tests the complete workflow of the MCP server,
including all 5 core tools and their integration.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.index.api_index import APIIndex
from src.index.index_builder import IndexBuilder
from src.docs.document_store import DocumentStore
from src.docs.doc_chunker import DocChunker
from src.invoker.handle_registry import HandleRegistry
from src.invoker.parameter_parser import ParameterParser
from src.invoker.api_invoker import APIInvoker
from src.security.path_validator import PathValidator
from src.security.sandbox import Sandbox


# ============================================================================
# Test Configuration
# ============================================================================
PROJECT_ROOT = Path(__file__).parent.parent
INDEX_PATH = PROJECT_ROOT / "data" / "api_index.json"
DOCS_PATH = PROJECT_ROOT / "klayout-doc" / "markdown_docs"


# ============================================================================
# Test Fixtures
# ============================================================================
@pytest.fixture
def api_index():
    """Create and load API index."""
    if INDEX_PATH.exists():
        return APIIndex(str(INDEX_PATH))
    return None


@pytest.fixture
def doc_store():
    """Create document store."""
    if DOCS_PATH.exists():
        return DocumentStore(str(DOCS_PATH))
    return None


@pytest.fixture
def registry():
    """Create handle registry."""
    return HandleRegistry()


@pytest.fixture
def invoker(registry):
    """Create API invoker."""
    sandbox = Sandbox()
    return APIInvoker(registry, sandbox)


# ============================================================================
# Index System Tests
# ============================================================================
class TestAPIIndex:
    """Tests for the API Index system."""
    
    def test_index_loads(self, api_index):
        """Test that the index loads successfully."""
        if api_index is None:
            pytest.skip("Index file not found")
        assert api_index.is_loaded()
    
    def test_index_stats(self, api_index):
        """Test index statistics."""
        if api_index is None:
            pytest.skip("Index file not found")
        stats = api_index.get_stats()
        assert stats["total_classes"] > 0
        assert stats["total_modules"] > 0
    
    def test_search_class(self, api_index):
        """Test searching for a class."""
        if api_index is None:
            pytest.skip("Index file not found")
        results = api_index.search("Box", limit=5)
        assert len(results) > 0
        # Box should be the top result
        assert any(r.name == "Box" and r.type == "class" for r in results)
    
    def test_search_method(self, api_index):
        """Test searching for a method."""
        if api_index is None:
            pytest.skip("Index file not found")
        results = api_index.search("area", search_type="method", limit=10)
        assert len(results) > 0
        assert all(r.type == "method" for r in results)
    
    def test_get_class(self, api_index):
        """Test getting class details."""
        if api_index is None:
            pytest.skip("Index file not found")
        box_class = api_index.get_class("Box")
        assert box_class is not None
        assert box_class["module"] == "db"
    
    def test_get_method(self, api_index):
        """Test getting method details."""
        if api_index is None:
            pytest.skip("Index file not found")
        method = api_index.get_method("Box", "area")
        assert method is not None
        assert method["name"] == "area"
    
    def test_list_modules(self, api_index):
        """Test listing modules."""
        if api_index is None:
            pytest.skip("Index file not found")
        modules = api_index.list_modules()
        assert "db" in modules
        assert len(modules) > 0


# ============================================================================
# Document System Tests
# ============================================================================
class TestDocumentStore:
    """Tests for the Document Store."""
    
    def test_get_class_doc(self, doc_store):
        """Test getting class documentation."""
        if doc_store is None:
            pytest.skip("Docs not found")
        doc = doc_store.get_class_doc("Box")
        assert doc is not None
        assert len(doc) > 0
        assert "Box" in doc
    
    def test_get_method_doc(self, doc_store):
        """Test getting method documentation."""
        if doc_store is None:
            pytest.skip("Docs not found")
        doc = doc_store.get_method_doc("Box", "area")
        assert doc is not None
        assert "area" in doc
    
    def test_list_topics(self, doc_store):
        """Test listing topics."""
        if doc_store is None:
            pytest.skip("Docs not found")
        topics = doc_store.list_topics()
        assert len(topics) > 0
    
    def test_cache_stats(self, doc_store):
        """Test cache statistics."""
        if doc_store is None:
            pytest.skip("Docs not found")
        # Access some docs to populate cache
        doc_store.get_class_doc("Box")
        stats = doc_store.get_cache_stats()
        assert stats["cache_size"] > 0


class TestDocChunker:
    """Tests for the Document Chunker."""
    
    def test_chunk_class_doc(self, doc_store):
        """Test chunking class documentation."""
        if doc_store is None:
            pytest.skip("Docs not found")
        doc = doc_store.get_class_doc("Box")
        if doc is None:
            pytest.skip("Box doc not found")
        
        chunker = DocChunker()
        chunks = chunker.chunk_class_doc(doc, "Box")
        assert len(chunks) > 0
    
    def test_extract_examples(self, doc_store):
        """Test extracting code examples."""
        if doc_store is None:
            pytest.skip("Docs not found")
        doc = doc_store.get_class_doc("Box")
        if doc is None:
            pytest.skip("Box doc not found")
        
        chunker = DocChunker()
        examples = chunker.extract_examples(doc)
        # May or may not have examples
        assert isinstance(examples, list)


# ============================================================================
# Handle Registry Tests
# ============================================================================
class TestHandleRegistry:
    """Tests for the Handle Registry."""
    
    def test_register_and_get(self, registry):
        """Test registering and getting objects."""
        obj = {"test": "value"}
        handle = registry.register(obj, "dict", module="test")
        assert handle is not None
        assert registry.get(handle) == obj
    
    def test_alias(self, registry):
        """Test handle aliases."""
        obj = {"test": "value"}
        handle = registry.register(obj, "dict", alias="my_dict")
        
        # Get by alias
        assert registry.get("my_dict") == obj
        
        # Get by handle
        assert registry.get(handle) == obj
    
    def test_release(self, registry):
        """Test releasing handles."""
        obj = {"test": "value"}
        handle = registry.register(obj, "dict")
        
        assert registry.release(handle)
        assert registry.get(handle) is None
    
    def test_list_handles(self, registry):
        """Test listing handles."""
        registry.register({"a": 1}, "dict", module="test")
        registry.register({"b": 2}, "dict", module="test")
        
        handles = registry.list_handles()
        assert len(handles) == 2
    
    def test_filter_by_type(self, registry):
        """Test filtering handles by type."""
        registry.register({"a": 1}, "dict")
        registry.register([1, 2, 3], "list")
        
        dict_handles = registry.list_handles(filter_type="dict")
        assert len(dict_handles) == 1
        assert dict_handles[0].obj_type == "dict"


# ============================================================================
# API Invoker Tests
# ============================================================================
class TestAPIInvoker:
    """Tests for the API Invoker."""
    
    def test_check_klayout_available(self, invoker):
        """Test KLayout availability check."""
        available = invoker.check_klayout_available()
        # Should be True in the test environment
        assert isinstance(available, bool)
    
    @pytest.mark.skipif(
        not APIInvoker(HandleRegistry()).check_klayout_available(),
        reason="KLayout not available"
    )
    def test_invoke_constructor(self, invoker):
        """Test invoking a constructor."""
        result = invoker.invoke_constructor(
            "Box", "db",
            {"left": 0, "bottom": 0, "right": 100, "top": 100}
        )
        assert result.success
        assert result.return_handle is not None
        assert result.return_type == "Box"
    
    @pytest.mark.skipif(
        not APIInvoker(HandleRegistry()).check_klayout_available(),
        reason="KLayout not available"
    )
    def test_invoke_method(self, invoker, registry):
        """Test invoking a method."""
        # First create an object
        create_result = invoker.invoke_constructor(
            "Box", "db",
            {"left": 0, "bottom": 0, "right": 100, "top": 100}
        )
        assert create_result.success
        
        # Then call a method
        result = invoker.invoke_method(create_result.return_handle, "area")
        assert result.success
        assert result.return_value == 10000.0


# ============================================================================
# Security Tests
# ============================================================================
class TestPathValidator:
    """Tests for Path Validator."""
    
    def test_safe_path(self):
        """Test validating a safe path."""
        validator = PathValidator(allowed_read_dirs=["/tmp"])
        result = validator.validate_read_path("/tmp/test.gds")
        assert result.valid
    
    def test_dangerous_traversal(self):
        """Test blocking directory traversal."""
        validator = PathValidator(allowed_read_dirs=["/tmp"])
        result = validator.validate_read_path("../../../etc/passwd")
        assert not result.valid
        assert "dangerous pattern" in result.error.lower()
    
    def test_blocked_system_path(self):
        """Test blocking system paths."""
        validator = PathValidator(allowed_read_dirs=["/tmp"])
        result = validator.validate_read_path("/etc/passwd")
        assert not result.valid


class TestSandbox:
    """Tests for Sandbox."""
    
    def test_allowed_call(self):
        """Test allowing safe API calls."""
        sandbox = Sandbox()
        assert sandbox.check_api_call("Box", "area")
    
    def test_blocked_class(self):
        """Test blocking dangerous classes."""
        sandbox = Sandbox()
        assert not sandbox.check_api_call("QProcess", "start")
    
    def test_blocked_pattern(self):
        """Test blocking by pattern."""
        sandbox = Sandbox()
        assert not sandbox.check_api_call("MyClass", "network_connect")


# ============================================================================
# Integration Tests
# ============================================================================
class TestIntegration:
    """Integration tests for the complete workflow."""
    
    @pytest.mark.skipif(
        not APIInvoker(HandleRegistry()).check_klayout_available(),
        reason="KLayout not available"
    )
    def test_full_workflow(self, api_index, doc_store, invoker, registry):
        """Test complete workflow: search -> describe -> create -> call."""
        if api_index is None:
            pytest.skip("Index not available")
        
        # 1. Search for Box
        results = api_index.search("Box", module="db", limit=5)
        assert any(r.name == "Box" for r in results)
        
        # 2. Get Box class info
        box_info = api_index.get_class("Box")
        assert box_info is not None
        
        # 3. Create a Box
        result = invoker.invoke_constructor(
            "Box", "db",
            {"left": 0, "bottom": 0, "right": 50, "top": 50}
        )
        assert result.success
        box_handle = result.return_handle
        
        # 4. Call methods
        area = invoker.invoke_method(box_handle, "area")
        assert area.success
        assert area.return_value == 2500.0
        
        width = invoker.invoke_method(box_handle, "width")
        assert width.success
        assert width.return_value == 50
        
        # 5. Verify handle exists
        handles = registry.list_handles(filter_type="Box")
        assert len(handles) == 1
        
        # 6. Release handle
        registry.release(box_handle)
        assert registry.get(box_handle) is None


# ============================================================================
# Run Tests
# ============================================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
