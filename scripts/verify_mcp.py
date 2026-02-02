#!/usr/bin/env python3
"""
KLayout MCP Server - Complete Verification Suite

This script performs comprehensive verification of the KLayout MCP server:
1. Environment checks
2. Dependency validation
3. Import tests
4. Tool functionality tests
5. Resource tests
6. Error handling tests
7. Async/Context integration tests

Usage:
    python scripts/verify_mcp.py [--verbose] [--skip-klayout]

Exit codes:
    0 - All tests passed
    1 - Some tests failed
    2 - Critical environment issue
"""

import sys
import asyncio
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    passed: bool
    message: str = ""
    duration_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


class TestRunner:
    """Runs verification tests and collects results."""
    
    def __init__(self, verbose: bool = False, skip_klayout: bool = False):
        self.verbose = verbose
        self.skip_klayout = skip_klayout
        self.results: List[TestResult] = []
        self.start_time: Optional[datetime] = None
        
    def log(self, message: str, level: str = "INFO"):
        """Log a message if verbose mode is on."""
        if self.verbose or level in ["ERROR", "WARN"]:
            prefix = {"INFO": "  ", "WARN": "⚠️ ", "ERROR": "❌", "SUCCESS": "✅"}.get(level, "  ")
            print(f"{prefix} {message}")
    
    def add_result(self, result: TestResult):
        """Add a test result."""
        self.results.append(result)
        status = "✅ PASS" if result.passed else "❌ FAIL"
        if not result.passed or self.verbose:
            print(f"{status}: {result.name}")
            if result.message:
                print(f"       {result.message}")
    
    def run_test(self, name: str, test_func) -> TestResult:
        """Run a single test function."""
        import time
        start = time.time()
        try:
            result = test_func()
            if isinstance(result, tuple):
                passed, message = result
                result = TestResult(name, passed, message)
            elif isinstance(result, bool):
                result = TestResult(name, result)
            else:
                result = TestResult(name, True, str(result))
        except Exception as e:
            result = TestResult(name, False, f"Exception: {e}")
        result.duration_ms = (time.time() - start) * 1000
        self.add_result(result)
        return result
    
    # ==================== Phase 1: Environment Checks ====================
    
    def check_python_version(self) -> TestResult:
        """Check Python version is 3.8+."""
        version = sys.version_info
        passed = version >= (3, 8)
        message = f"Python {version.major}.{version.minor}.{version.micro}"
        return TestResult("Python Version", passed, message)
    
    def check_project_structure(self) -> TestResult:
        """Check all required files exist."""
        root = Path(__file__).parent.parent
        required_files = [
            "pyproject.toml",
            "src/server.py",
            "src/models.py",
            "data/api_index.json",
            "evaluation.xml"
        ]
        missing = []
        for file in required_files:
            if not (root / file).exists():
                missing.append(file)
        
        # Check requirements.txt should NOT exist
        if (root / "requirements.txt").exists():
            missing.append("requirements.txt (should be removed)")
        
        passed = len(missing) == 0
        message = f"Missing: {', '.join(missing)}" if missing else "All required files present"
        return TestResult("Project Structure", passed, message)
    
    def check_pyproject_toml(self) -> TestResult:
        """Check pyproject.toml is valid."""
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            import tomli as tomllib
        
        root = Path(__file__).parent.parent
        try:
            with open(root / "pyproject.toml", "rb") as f:
                config = tomllib.load(f)
            
            checks = [
                ("project", "name"),
                ("project", "version"),
                ("project", "license"),
                ("project", "dependencies"),
            ]
            
            missing = []
            for section, key in checks:
                if section not in config or key not in config.get(section, {}):
                    missing.append(f"{section}.{key}")
            
            # Check for asyncio pytest config
            has_asyncio = "tool" in config and "pytest" in config["tool"] and "ini_options" in config["tool"]["pytest"]
            
            passed = len(missing) == 0
            message = f"License: {config['project'].get('license', 'N/A')}, pytest-asyncio: {has_asyncio}"
            return TestResult("pyproject.toml", passed, message)
        except Exception as e:
            return TestResult("pyproject.toml", False, str(e))
    
    # ==================== Phase 2: Dependency Validation ====================
    
    def check_mcp_installed(self) -> TestResult:
        """Check MCP SDK is installed."""
        try:
            import mcp
            from mcp.server import FastMCP
            from mcp.server.fastmcp import Context
            version = getattr(mcp, "__version__", "unknown")
            return TestResult("MCP SDK", True, f"Version: {version}")
        except ImportError as e:
            return TestResult("MCP SDK", False, f"Not installed: {e}")
    
    def check_pydantic_installed(self) -> TestResult:
        """Check Pydantic v2 is installed."""
        try:
            import pydantic
            version = pydantic.__version__
            is_v2 = version.startswith("2.")
            return TestResult("Pydantic", is_v2, f"Version: {version}")
        except ImportError:
            return TestResult("Pydantic", False, "Not installed")
    
    def check_klayout_available(self) -> TestResult:
        """Check KLayout availability."""
        if self.skip_klayout:
            return TestResult("KLayout", True, "Skipped (--skip-klayout)")
        
        try:
            # Try standalone first
            import klayout.db
            return TestResult("KLayout", True, "Standalone mode available")
        except ImportError:
            try:
                import pya
                return TestResult("KLayout", True, "GUI mode (pya) available")
            except ImportError:
                return TestResult("KLayout", True, "Not installed (optional)")
    
    # ==================== Phase 3: Import Tests ====================
    
    def check_models_import(self) -> TestResult:
        """Check models can be imported."""
        try:
            from src.models import (
                SearchAPIInput, CallAPIInput, ManageHandlesInput,
                SearchAPIResponse, CallAPIResponse
            )
            return TestResult("Import Models", True, "All models imported")
        except Exception as e:
            return TestResult("Import Models", False, str(e))
    
    def check_server_import(self) -> TestResult:
        """Check server module can be imported."""
        try:
            from src.server import mcp, _init_components_async
            return TestResult("Import Server", True, "Server module loaded")
        except Exception as e:
            return TestResult("Import Server", False, str(e))
    
    def check_tools_import(self) -> TestResult:
        """Check tool modules can be imported."""
        try:
            from src.tools.search_api import SearchAPITool
            from src.tools.call_api import CallAPITool
            from src.tools.manage_handles import ManageHandlesTool
            return TestResult("Import Tools", True, "All tools imported")
        except Exception as e:
            return TestResult("Import Tools", False, str(e))
    
    # ==================== Phase 4: Async/Context Tests ====================
    
    async def test_async_initialization(self) -> TestResult:
        """Test async initialization."""
        try:
            from src.server import _init_components_async, _api_index
            
            # Reset state
            import src.server as server_module
            server_module._api_index = None
            
            # Test async init
            await _init_components_async()
            
            passed = server_module._api_index is not None
            return TestResult("Async Initialization", passed, "Components initialized")
        except Exception as e:
            return TestResult("Async Initialization", False, str(e))
    
    def check_async_syntax(self) -> TestResult:
        """Check server.py has proper async syntax."""
        root = Path(__file__).parent.parent
        server_file = root / "src/server.py"
        content = server_file.read_text()
        
        checks = {
            "async def": content.count("async def"),
            "await ": content.count("await "),
            "asyncio": "import asyncio" in content,
            "asyncio.Lock": "asyncio.Lock" in content,
            "run_in_executor": "run_in_executor" in content,
        }
        
        all_present = all([
            checks["async def"] >= 10,
            checks["await "] >= 50,
            checks["asyncio"],
            checks["asyncio.Lock"],
            checks["run_in_executor"]
        ])
        
        details = f"async def: {checks['async def']}, await: {checks['await ']}"
        return TestResult("Async Syntax", all_present, details)
    
    def check_context_usage(self) -> TestResult:
        """Check Context parameter usage."""
        root = Path(__file__).parent.parent
        server_file = root / "src/server.py"
        content = server_file.read_text()
        
        checks = {
            "Context import": "from mcp.server.fastmcp import Context" in content,
            "ctx: Context": "ctx: Context" in content,
            "report_progress": "ctx.report_progress" in content,
            "log_info": "ctx.log_info" in content,
        }
        
        all_present = all(checks.values())
        return TestResult("Context Usage", all_present, f"Features: {sum(checks.values())}/{len(checks)}")
    
    # ==================== Phase 5: Tool Definition Tests ====================
    
    def check_structured_output(self) -> TestResult:
        """Check structured_output is used."""
        root = Path(__file__).parent.parent
        server_file = root / "src/server.py"
        content = server_file.read_text()
        
        count = content.count("structured_output=True")
        passed = count >= 7  # At least 7 tools should have it
        return TestResult("Structured Output", passed, f"{count} tools enabled")
    
    def check_tool_annotations(self) -> TestResult:
        """Check tool annotations are present."""
        root = Path(__file__).parent.parent
        server_file = root / "src/server.py"
        content = server_file.read_text()
        
        required_annotations = ["readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint"]
        found = sum(1 for ann in required_annotations if ann in content)
        
        passed = found == len(required_annotations)
        return TestResult("Tool Annotations", passed, f"{found}/{len(required_annotations)} annotation types")
    
    # ==================== Phase 6: Functional Tests ====================
    
    async def test_api_index_loaded(self) -> TestResult:
        """Test API index can be loaded."""
        try:
            from src.index.api_index import APIIndex
            root = Path(__file__).parent.parent
            index_path = root / "data/api_index.json"
            
            if not index_path.exists():
                return TestResult("API Index Load", False, "Index file not found")
            
            index = APIIndex(str(index_path))
            loaded = index.is_loaded()
            stats = index.get_stats() if loaded else {}
            
            message = f"Classes: {stats.get('total_classes', 0)}, Modules: {stats.get('total_modules', 0)}"
            return TestResult("API Index Load", loaded, message)
        except Exception as e:
            return TestResult("API Index Load", False, str(e))
    
    async def test_search_functionality(self) -> TestResult:
        """Test search functionality."""
        try:
            from src.index.api_index import APIIndex
            from src.tools.search_api import SearchAPITool
            
            root = Path(__file__).parent.parent
            index = APIIndex(str(root / "data/api_index.json"))
            
            if not index.is_loaded():
                return TestResult("Search Function", False, "Index not loaded")
            
            tool = SearchAPITool(index)
            results = tool.search("Box", module="db", limit=5)
            
            has_results = len(results.get("results", [])) > 0
            return TestResult("Search Function", has_results, f"Found {len(results.get('results', []))} results")
        except Exception as e:
            return TestResult("Search Function", False, str(e))
    
    async def test_handle_registry(self) -> TestResult:
        """Test handle registry."""
        try:
            from src.invoker.handle_registry import HandleRegistry
            
            registry = HandleRegistry()
            obj = {"test": "value"}
            handle = registry.register(obj, "dict", alias="test_obj")
            
            retrieved = registry.get("test_obj")
            passed = retrieved == obj
            
            return TestResult("Handle Registry", passed, f"Handle: {handle}")
        except Exception as e:
            return TestResult("Handle Registry", False, str(e))
    
    # ==================== Phase 7: Integration Tests ====================
    
    async def test_end_to_end_workflow(self) -> TestResult:
        """Test complete workflow."""
        if self.skip_klayout:
            return TestResult("E2E Workflow", True, "Skipped (KLayout not available)")
        
        try:
            from src.invoker.klayout_compat import get_klayout_compat
            from src.invoker.handle_registry import HandleRegistry
            from src.security.sandbox import Sandbox
            from src.invoker.api_invoker import APIInvoker
            
            compat = get_klayout_compat()
            if not compat.is_available:
                return TestResult("E2E Workflow", True, "Skipped (KLayout not installed)")
            
            # Create components
            registry = HandleRegistry()
            sandbox = Sandbox()
            invoker = APIInvoker(registry, sandbox)
            
            # Try to create a Box
            result = invoker.invoke_constructor("Box", "db", {"left": 0, "bottom": 0, "right": 100, "top": 100})
            
            if result.success and result.return_handle:
                # Try to call area method
                area_result = invoker.invoke_method(result.return_handle, "area")
                passed = area_result.success and area_result.return_value == 10000.0
                return TestResult("E2E Workflow", passed, f"Box area: {area_result.return_value}")
            else:
                return TestResult("E2E Workflow", False, f"Constructor failed: {result.error}")
                
        except Exception as e:
            return TestResult("E2E Workflow", False, str(e))
    
    # ==================== Main Runner ====================
    
    async def run_all_tests(self) -> bool:
        """Run all verification tests."""
        print("=" * 60)
        print("KLayout MCP Server - Complete Verification")
        print("=" * 60)
        print()
        
        # Phase 1: Environment
        print("🔍 Phase 1: Environment Checks")
        print("-" * 40)
        self.run_test("Python Version", self.check_python_version)
        self.run_test("Project Structure", self.check_project_structure)
        self.run_test("pyproject.toml", self.check_pyproject_toml)
        print()
        
        # Phase 2: Dependencies
        print("🔍 Phase 2: Dependency Validation")
        print("-" * 40)
        self.run_test("MCP SDK", self.check_mcp_installed)
        self.run_test("Pydantic", self.check_pydantic_installed)
        self.run_test("KLayout", self.check_klayout_available)
        print()
        
        # Phase 3: Imports
        print("🔍 Phase 3: Import Tests")
        print("-" * 40)
        self.run_test("Models Import", self.check_models_import)
        self.run_test("Server Import", self.check_server_import)
        self.run_test("Tools Import", self.check_tools_import)
        print()
        
        # Phase 4: Async/Context
        print("🔍 Phase 4: Async & Context Integration")
        print("-" * 40)
        self.run_test("Async Syntax", self.check_async_syntax)
        self.run_test("Context Usage", self.check_context_usage)
        await self.test_async_initialization()
        print()
        
        # Phase 5: Tool Definitions
        print("🔍 Phase 5: Tool Definition Validation")
        print("-" * 40)
        self.run_test("Structured Output", self.check_structured_output)
        self.run_test("Tool Annotations", self.check_tool_annotations)
        print()
        
        # Phase 6: Functional
        print("🔍 Phase 6: Functional Tests")
        print("-" * 40)
        await self.test_api_index_loaded()
        await self.test_search_functionality()
        await self.test_handle_registry()
        print()
        
        # Phase 7: Integration
        print("🔍 Phase 7: Integration Tests")
        print("-" * 40)
        await self.test_end_to_end_workflow()
        print()
        
        # Summary
        print("=" * 60)
        print("Verification Summary")
        print("=" * 60)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        
        if failed > 0:
            print()
            print("Failed Tests:")
            for r in self.results:
                if not r.passed:
                    print(f"  - {r.name}: {r.message}")
        
        total_time = sum(r.duration_ms for r in self.results)
        print(f"\nTotal Time: {total_time:.0f}ms")
        
        return failed == 0


def main():
    parser = argparse.ArgumentParser(description="KLayout MCP Server Verification")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--skip-klayout", action="store_true", help="Skip KLayout-dependent tests")
    args = parser.parse_args()
    
    runner = TestRunner(verbose=args.verbose, skip_klayout=args.skip_klayout)
    
    try:
        success = asyncio.run(runner.run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Verification interrupted by user")
        sys.exit(2)
    except Exception as e:
        print(f"\n\n💥 Critical error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
