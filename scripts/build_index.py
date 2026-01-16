#!/usr/bin/env python3
"""
Build Index Script - Generate API index from markdown documentation

This script parses the KLayout markdown documentation and generates
a JSON index file for fast API lookup and search.

Usage:
    python scripts/build_index.py [docs_path] [output_path]
    
Examples:
    python scripts/build_index.py klayout-doc/markdown_docs data/api_index.json
    python scripts/build_index.py  # Uses default paths
"""

import sys
import time
import argparse
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.index.index_builder import IndexBuilder


def main():
    parser = argparse.ArgumentParser(
        description="Build KLayout API index from markdown documentation"
    )
    parser.add_argument(
        "docs_path",
        nargs="?",
        default="klayout-doc/markdown_docs",
        help="Path to markdown documentation directory (default: klayout-doc/markdown_docs)"
    )
    parser.add_argument(
        "output_path",
        nargs="?", 
        default="data/api_index.json",
        help="Output path for JSON index file (default: data/api_index.json)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Resolve paths relative to project root
    project_root = Path(__file__).parent.parent
    docs_path = project_root / args.docs_path
    output_path = project_root / args.output_path
    
    if not docs_path.exists():
        print(f"Error: Documentation path does not exist: {docs_path}")
        sys.exit(1)
    
    print(f"Building index from: {docs_path}")
    print(f"Output file: {output_path}")
    
    start_time = time.time()
    
    try:
        builder = IndexBuilder(str(docs_path))
        index = builder.build_index()
        builder.save_index(index, str(output_path))
        
        elapsed = time.time() - start_time
        
        print(f"\nIndex built successfully in {elapsed:.2f} seconds")
        print(f"  Total classes: {index['total_classes']}")
        print(f"  Total modules: {len(index.get('modules', {}))}")
        print(f"  Total keywords: {len(index.get('keyword_index', {}))}")
        
        if args.verbose:
            print("\nModules:")
            for module, classes in index.get('modules', {}).items():
                print(f"  {module}: {len(classes)} classes")
        
    except Exception as e:
        print(f"Error building index: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
