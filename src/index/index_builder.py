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
    hierarchy: List[str] = None  # Class inheritance chain
    keywords: List[str] = None   # Extracted keywords for search
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
        if self.hierarchy is None:
            self.hierarchy = []
        if self.keywords is None:
            self.keywords = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "module": self.module,
            "description": self.description,
            "file_path": self.file_path,
            "hierarchy": self.hierarchy,
            "keywords": self.keywords,
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
        modules: Dict[str, List[str]] = {}  # module -> list of class names

        # Find all markdown files in the code directory
        code_path = self.docs_path / "code"
        if code_path.exists():
            md_files = list(code_path.glob("*.md"))
        else:
            md_files = list(self.docs_path.glob("**/*.md"))

        for md_file in md_files:
            try:
                api_class = self._parse_markdown_file(md_file)
                if api_class:
                    classes[api_class.name] = api_class
                    # Build module index
                    if api_class.module not in modules:
                        modules[api_class.module] = []
                    modules[api_class.module].append(api_class.name)
            except Exception as e:
                print(f"Warning: Failed to parse {md_file}: {e}")

        # Build keyword search index
        keyword_index = self._build_keyword_index(classes)

        # Convert to dictionary format
        index = {
            "version": "1.0.0",
            "total_classes": len(classes),
            "modules": modules,
            "classes": {name: cls.to_dict() for name, cls in classes.items()},
            "keyword_index": keyword_index,
        }

        return index

    def _build_keyword_index(self, classes: Dict[str, 'APIClass']) -> Dict[str, List[str]]:
        """
        Build a keyword-to-classes index for fast searching.
        
        Args:
            classes: Dictionary of class name to APIClass
            
        Returns:
            Dictionary mapping keywords to list of class names
        """
        keyword_index: Dict[str, List[str]] = {}
        
        for class_name, api_class in classes.items():
            # Add class name keywords
            for keyword in api_class.keywords:
                kw_lower = keyword.lower()
                if kw_lower not in keyword_index:
                    keyword_index[kw_lower] = []
                if class_name not in keyword_index[kw_lower]:
                    keyword_index[kw_lower].append(class_name)
            
            # Add method names as keywords
            all_methods = (api_class.methods + api_class.constructors + 
                         api_class.static_methods)
            for method in all_methods:
                method_lower = method.name.lower()
                if method_lower not in keyword_index:
                    keyword_index[method_lower] = []
                if class_name not in keyword_index[method_lower]:
                    keyword_index[method_lower].append(class_name)
        
        return keyword_index

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

        # Extract class name from filename (remove class_ prefix)
        class_name = file_path.stem
        if class_name.startswith("class_"):
            class_name = class_name[6:]  # Remove "class_" prefix
        
        # Handle nested class names (++ becomes ::)
        class_name = class_name.replace("++", "::")

        # Extract module (db, lay, etc.)
        module = self._extract_module(content)

        # Extract description
        description = self._extract_description(content)
        
        # Extract class hierarchy
        hierarchy = self._extract_hierarchy(content)
        
        # Extract keywords from class name and description
        keywords = self._extract_keywords(class_name, description, content)

        # Extract methods from Detailed description section (more reliable format)
        all_methods = self._extract_methods_from_detailed(content)
        
        # Categorize methods
        constructors = [m for m in all_methods if m.name == 'new' or m.name == class_name]
        static_methods = [m for m in all_methods if m.is_static and m not in constructors]
        deprecated_methods = [m for m in all_methods if m.is_deprecated]
        regular_methods = [m for m in all_methods if m not in constructors 
                         and m not in static_methods and m not in deprecated_methods]

        return APIClass(
            name=class_name,
            module=module,
            description=description,
            file_path=str(file_path),
            hierarchy=hierarchy,
            keywords=keywords,
            methods=regular_methods,
            constructors=constructors,
            static_methods=static_methods,
            deprecated_methods=deprecated_methods,
        )

    def _extract_methods_from_detailed(self, content: str) -> List[APIMethod]:
        """
        Extract methods from the Detailed description section.
        This section has a more reliable format with ### method_name headers.
        
        Args:
            content: Full markdown content
            
        Returns:
            List of APIMethod objects
        """
        methods = []
        
        # Find Detailed description section
        detail_match = re.search(r'##\s*Detailed description(.*?)$', content, re.DOTALL | re.IGNORECASE)
        if not detail_match:
            return methods
        
        detail_content = detail_match.group(1)
        
        # Find all method headers: ### method_name
        # Method headers are followed by Signature: and Description:
        method_blocks = re.split(r'###\s+', detail_content)
        
        for block in method_blocks[1:]:  # Skip first empty block
            if not block.strip():
                continue
            
            # Extract method name (first line or word before any special char)
            lines = block.split('\n', 1)
            if not lines:
                continue
                
            # Method name is the first word/symbol
            first_line = lines[0].strip()
            # Handle method names like "!=", "&", "*", etc.
            method_name_match = re.match(r'^([^\s|]+)', first_line)
            if not method_name_match:
                continue
            method_name = method_name_match.group(1).strip()
            
            # Skip empty or invalid names
            if not method_name or method_name == '|':
                continue
            
            # Extract signature
            sig_match = re.search(r'Signature:\s*(\[[^\]]*\])?\s*([^\n]+)', block)
            signature = ''
            return_type = 'void'
            is_static = False
            is_const = False
            
            if sig_match:
                modifiers = sig_match.group(1) or ''
                signature = sig_match.group(2).strip()
                is_static = '[static]' in modifiers
                is_const = '[const]' in modifiers or '[const]' in signature
                
                # Extract return type from signature
                # Format: return_type method_name (params)
                ret_match = re.match(r'^([^(]+?)\s+\w+\s*\(', signature)
                if ret_match:
                    return_type = ret_match.group(1).strip()
                    return_type = re.sub(r'\[const\]', '', return_type).strip()
            
            # Extract description
            desc_match = re.search(r'Description:\s*([^\n|]+)', block)
            description = desc_match.group(1).strip() if desc_match else ''
            
            # Check if deprecated
            is_deprecated = 'deprecated' in block.lower() and 'use of this method is deprecated' in block.lower()
            
            # Build clean signature
            if not signature:
                signature = f"{method_name}()"
            
            methods.append(APIMethod(
                name=method_name,
                signature=signature,
                return_type=return_type,
                description=description[:200],
                is_static=is_static,
                is_const=is_const,
                is_deprecated=is_deprecated,
                parameters=[]
            ))
        
        return methods

    def _extract_hierarchy(self, content: str) -> List[str]:
        """Extract class hierarchy from content."""
        # Look for "Class hierarchy:" pattern
        match = re.search(r'Class hierarchy:\s*([^\n]+)', content)
        if match:
            hierarchy_str = match.group(1).strip()
            # Split by » character
            parts = [p.strip() for p in hierarchy_str.split('»')]
            return [p for p in parts if p]
        return []

    def _extract_keywords(self, class_name: str, description: str, content: str) -> List[str]:
        """
        Extract keywords from class name and description for search indexing.
        
        Args:
            class_name: The class name
            description: The class description
            content: Full markdown content
            
        Returns:
            List of keywords
        """
        keywords = set()
        
        # Add class name and its parts
        keywords.add(class_name.lower())
        
        # Split camelCase and add parts
        parts = re.findall(r'[A-Z][a-z]*|[a-z]+', class_name)
        for part in parts:
            if len(part) > 2:
                keywords.add(part.lower())
        
        # Extract important words from description
        # Common stopwords to filter out
        stopwords = {'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been',
                    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                    'would', 'could', 'should', 'may', 'might', 'can', 'this',
                    'that', 'these', 'those', 'it', 'its', 'of', 'for', 'to',
                    'in', 'on', 'at', 'by', 'with', 'from', 'as', 'or', 'and',
                    'not', 'no', 'if', 'then', 'else', 'when', 'where', 'which',
                    'who', 'whom', 'what', 'how', 'all', 'each', 'every', 'both',
                    'few', 'more', 'most', 'other', 'some', 'such', 'only', 'own',
                    'same', 'so', 'than', 'too', 'very', 'just', 'also', 'now'}
        
        # Extract words from description
        desc_words = re.findall(r'\b[a-zA-Z]{3,}\b', description.lower())
        for word in desc_words:
            if word not in stopwords:
                keywords.add(word)
        
        return list(keywords)[:20]  # Limit to 20 keywords

    def _extract_module(self, content: str) -> str:
        """Extract module name from content."""
        # Try pattern: Module: xxx Description: or Module: xxx followed by newline/space
        match = re.search(r'Module:\s*(\w+)(?:\s+Description:|[\s\n])', content)
        if match:
            return match.group(1)
        # Fallback: simpler pattern
        match = re.search(r'Module:\s*(\w+)', content)
        return match.group(1) if match else "unknown"

    def _extract_description(self, content: str) -> str:
        """Extract class description from content."""
        # Look for description after "Description:" - can be on same line or multi-line
        # Pattern: Description: text until next section marker or double newline
        match = re.search(r'Description:\s*(.+?)(?:\s*-\s*\[|\s*##|\n\n)', content, re.DOTALL)
        if match:
            desc = match.group(1).strip()
            # Clean up - remove markdown links and extra whitespace
            desc = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', desc)
            desc = re.sub(r'\s+', ' ', desc)
            return desc[:500]  # Limit to 500 characters
        
        # Fallback: try simpler pattern
        match = re.search(r'Description:\s*([^\n]+)', content)
        if match:
            desc = match.group(1).strip()
            desc = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', desc)
            return desc[:500]

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

        # Find the section (handle both "##" and "## " patterns)
        # The content might be on a single line, so use a flexible pattern
        section_pattern = rf'##\s*{re.escape(section_name)}(.*?)(?=##\s*[A-Z]|$)'
        section_match = re.search(section_pattern, content, re.DOTALL | re.IGNORECASE)

        if not section_match:
            return methods

        section_content = section_match.group(1)
        
        # Split the section content to find individual table rows
        # Table rows start with | and contain **method_name**
        # Pattern to match table cells: | cell1 | cell2 | **name** | params | desc |
        
        # First, find all method name patterns in the section
        method_patterns = re.findall(
            r'\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*\*\*([^*|]+)\*\*\s*\|\s*([^|]*?)\s*\|\s*([^|]+?)(?=\s*\|(?:\s*[^|]*\s*\|(?:\s*[^|]*\s*\|)?\s*\*\*|\s*$|\s*##))',
            section_content
        )
        
        if not method_patterns:
            # Try alternate pattern for constructor format (3 columns before description)
            method_patterns = re.findall(
                r'\|\s*([^|]+?)\s*\|\s*\*\*([^*]+)\*\*\s*\|\s*([^|]*?)\s*\|\s*([^|]+?)(?=\s*\|(?:\s*[^|]*?\s*\|)?\s*\*\*|\s*##|\s*$)',
                section_content
            )
            
            if method_patterns:
                # Reformat to match expected structure
                method_patterns = [(m[0], '', m[1], m[2], m[3]) for m in method_patterns]

        seen_methods = set()
        for match in method_patterns:
            if len(match) >= 5:
                col1, col2, method_name, params, description = match[0], match[1], match[2], match[3], match[4]
            elif len(match) == 4:
                col1, method_name, params, description = match
                col2 = ''
            else:
                continue
            
            # Clean up values
            method_name = method_name.strip()
            params = params.strip()
            description = description.strip()
            
            # Determine return type from col1 and col2
            return_type = col2.strip() if col2.strip() else col1.strip()
            
            # Skip table header separators
            if '---' in method_name or not method_name or method_name == '---':
                continue
            
            # Skip if description looks like a header separator
            if description.startswith('---'):
                continue
                
            # Skip internal methods (starting with _) unless they're special
            if method_name.startswith('_') and method_name not in ['__init__', '__str__', '__repr__']:
                continue
            
            # Create unique key to avoid duplicates
            method_key = f"{method_name}"
            if method_key in seen_methods:
                continue
            seen_methods.add(method_key)

            # Build signature
            params_clean = params.strip('()')
            if params_clean:
                signature = f"{method_name}({params_clean})"
            else:
                signature = f"{method_name}()"

            # Clean return type
            return_type = re.sub(r'\*?\[?const\]?\*?', '', return_type).strip()
            return_type = return_type.replace('*', '').strip()
            if not return_type or return_type == '---':
                return_type = 'void'

            # Parse parameters
            parameters = self._parse_parameters(params)

            methods.append(APIMethod(
                name=method_name,
                signature=signature,
                return_type=return_type,
                description=description[:200],
                is_static=is_static,
                is_const='[const]' in col1,
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