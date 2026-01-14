"""
Index Builder - Parse markdown docs to extract API metadata

This module parses KLayout markdown documentation files to extract
API metadata including class names, module names, methods, and descriptions.
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class APIMethod:
    """Represents a method in the API."""
    name: str
    signature: str
    return_type: str
    description: str
    is_static: bool = False
    is_const: bool = False
    is_deprecated: bool = False
    parameters: List[Dict[str, str]] = None

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []


@dataclass
class APIClass:
    """Represents a class in the KLayout API."""
    name: str
    module: str
    description: str
    file_path: str
    methods: List[APIMethod] = None
    constructors: List[APIMethod] = None
    static_methods: List[APIMethod] = None
    deprecated_methods: List[APIMethod] = None

    def __post_init__(self):
        if self.methods is None:
            self.methods = []
        if self.constructors is None:
            self.constructors = []
        if self.static_methods is None:
            self.static_methods = []
        if self.deprecated_methods is None:
            self.deprecated_methods = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "module": self.module,
            "description": self.description,
            "file_path": self.file_path,
            "methods": [asdict(m) for m in self.methods],
            "constructors": [asdict(m) for m in self.constructors],
            "static_methods": [asdict(m) for m in self.static_methods],
            "deprecated_methods": [asdict(m) for m in self.deprecated_methods],
        }


class IndexBuilder:
    """
    Builds an index of KLayout APIs from markdown documentation files.

    The index contains:
    - Class names and modules
    - Method signatures and descriptions
    - Parameter information
    - Deprecation status
    """

    def __init__(self, docs_path: str):
        """
        Initialize the IndexBuilder.

        Args:
            docs_path: Path to the markdown documentation directory
        """
        self.docs_path = Path(docs_path)
        if not self.docs_path.exists():
            raise ValueError(f"Documentation path does not exist: {docs_path}")

    def build_index(self) -> Dict[str, Any]:
        """
        Build the complete API index from all markdown files.

        Returns:
            Dictionary containing the complete API index
        """
        classes: Dict[str, APIClass] = {}

        # Find all markdown files in the code directory
        md_files = list(self.docs_path.glob("**/*.md"))

        for md_file in md_files:
            try:
                api_class = self._parse_markdown_file(md_file)
                if api_class:
                    classes[api_class.name] = api_class
            except Exception as e:
                print(f"Warning: Failed to parse {md_file}: {e}")

        # Convert to dictionary format
        index = {
            "version": "1.0.0",
            "total_classes": len(classes),
            "classes": {name: cls.to_dict() for name, cls in classes.items()},
        }

        return index

    def _parse_markdown_file(self, file_path: Path) -> Optional[APIClass]:
        """
        Parse a single markdown documentation file.

        Args:
            file_path: Path to the markdown file

        Returns:
            APIClass object or None if parsing fails
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None

        # Extract class name from filename
        class_name = file_path.stem

        # Extract module (db, lay, etc.)
        module = self._extract_module(content)

        # Extract description
        description = self._extract_description(content)

        # Extract methods from different sections
        constructors = self._extract_constructors(content)
        methods = self._extract_methods(content, "Public methods")
        static_methods = self._extract_methods(content, "Public static methods and constants")
        deprecated_methods = self._extract_methods(content, "Deprecated methods")

        return APIClass(
            name=class_name,
            module=module,
            description=description,
            file_path=str(file_path),
            methods=methods,
            constructors=constructors,
            static_methods=static_methods,
            deprecated_methods=deprecated_methods,
        )

    def _extract_module(self, content: str) -> str:
        """Extract module name from content."""
        match = re.search(r'Module:\s*(\w+)', content)
        return match.group(1) if match else "unknown"

    def _extract_description(self, content: str) -> str:
        """Extract class description from content."""
        # Look for description after "Description:" tag
        match = re.search(r'Description:\s*(.*?)\n\n', content, re.DOTALL)
        if match:
            desc = match.group(1).strip()
            # Clean up - remove markdown links and extra whitespace
            desc = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', desc)
            desc = re.sub(r'\s+', ' ', desc)
            return desc[:500]  # Limit to 500 characters

        return "No description available"

    def _extract_constructors(self, content: str) -> List[APIMethod]:
        """Extract constructor methods from content."""
        return self._parse_method_table(content, "Public constructors", is_constructor=True)

    def _extract_methods(self, content: str, section_name: str) -> List[APIMethod]:
        """
        Extract methods from a specific section.

        Args:
            content: Full markdown content
            section_name: Name of the section to parse

        Returns:
            List of APIMethod objects
        """
        is_static = "static" in section_name.lower()
        is_deprecated = "deprecated" in section_name.lower()

        return self._parse_method_table(content, section_name,
                                       is_static=is_static,
                                       is_deprecated=is_deprecated)

    def _parse_method_table(self, content: str, section_name: str,
                           is_constructor: bool = False,
                           is_static: bool = False,
                           is_deprecated: bool = False) -> List[APIMethod]:
        """
        Parse a method table from markdown content.

        Args:
            content: Full markdown content
            section_name: Name of the section containing the table
            is_constructor: Whether these are constructors
            is_static: Whether these are static methods
            is_deprecated: Whether these are deprecated methods

        Returns:
            List of APIMethod objects
        """
        methods = []

        # Find the section
        section_match = re.search(
            rf'## {re.escape(section_name)}(.*?)(?=##|$)',
            content,
            re.DOTALL
        )

        if not section_match:
            return methods

        section_content = section_match.group(1)

        # Parse markdown table rows
        # Table format: | const | return_type | **method_name** | params | description |
        rows = re.findall(r'\|\s*\[?const\]?\s*\|\s*([^|]+)\s*\|\s*\*\*([^*]+)\*\*\s*\|\s*([^|]*)\s*\|\s*([^|]+)',
                         section_content)

        for return_type, method_name, params, description in rows:
            # Clean up the extracted values
            return_type = return_type.strip()
            method_name = method_name.strip()
            params = params.strip()
            description = description.strip()

            # Skip internal methods (starting with _)
            if method_name.startswith('_'):
                continue

            # Build signature
            if params:
                signature = f"{method_name}({params})"
            else:
                signature = f"{method_name}()"

            # Determine if const
            is_const = '[const]' in return_type

            # Clean return type
            return_type = return_type.replace('[const]', '').replace('*', '').strip()

            # Parse parameters
            parameters = self._parse_parameters(params)

            methods.append(APIMethod(
                name=method_name,
                signature=signature,
                return_type=return_type,
                description=description[:200],  # Limit description length
                is_static=is_static,
                is_const=is_const,
                is_deprecated=is_deprecated,
                parameters=parameters
            ))

        return methods

    def _parse_parameters(self, params_str: str) -> List[Dict[str, str]]:
        """
        Parse parameter string into structured format.

        Args:
            params_str: Parameter string from markdown table

        Returns:
            List of parameter dictionaries
        """
        parameters = []

        if not params_str or params_str == '':
            return parameters

        # Split by commas (but careful with nested parentheses)
        # Simple approach: split by comma and clean up
        parts = [p.strip() for p in params_str.split(',')]

        for part in parts:
            if not part:
                continue

            # Try to extract type and name
            # Format: "type name" or just "name"
            match = re.match(r'^(\w+(?:\s*\w+)*)\s+(\w+)$', part)
            if match:
                param_type = match.group(1)
                param_name = match.group(2)
            else:
                param_type = "unknown"
                param_name = part

            parameters.append({
                "name": param_name,
                "type": param_type
            })

        return parameters

    def save_index(self, index: Dict[str, Any], output_path: str) -> None:
        """
        Save the index to a JSON file.

        Args:
            index: The index dictionary
            output_path: Path to save the JSON file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

        print(f"Index saved to {output_path}")
        print(f"Total classes: {index['total_classes']}")


def main():
    """Main entry point for command-line usage."""
    import sys

    if len(sys.argv) < 3:
        print("Usage: python index_builder.py <docs_path> <output_path>")
        sys.exit(1)

    docs_path = sys.argv[1]
    output_path = sys.argv[2]

    builder = IndexBuilder(docs_path)
    index = builder.build_index()
    builder.save_index(index, output_path)


if __name__ == "__main__":
    main()