"""
Parameter Parser - Parse and validate API parameters

This module handles parameter parsing, type conversion, and handle resolution
for KLayout API calls.
"""

import re
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass

from .handle_registry import HandleRegistry


@dataclass
class ParamDef:
    """Definition of a parameter."""
    name: str
    param_type: str
    default_value: Optional[Any] = None
    is_optional: bool = False


@dataclass
class ParsedParams:
    """Result of parameter parsing."""
    positional: List[Any]
    keyword: Dict[str, Any]
    errors: List[str]
    
    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


class ParameterParser:
    """
    Parses and validates parameters for API calls.
    
    Features:
    - Type conversion (string to int, float, bool)
    - Handle resolution (convert handle IDs to objects)
    - Default value handling
    - Validation against expected types
    """
    
    # Type mappings for conversion
    TYPE_CONVERTERS = {
        'int': int,
        'integer': int,
        'float': float,
        'double': float,
        'bool': lambda x: x.lower() in ('true', '1', 'yes') if isinstance(x, str) else bool(x),
        'boolean': lambda x: x.lower() in ('true', '1', 'yes') if isinstance(x, str) else bool(x),
        'string': str,
        'str': str,
    }
    
    def __init__(self, registry: Optional[HandleRegistry] = None):
        """
        Initialize the ParameterParser.
        
        Args:
            registry: HandleRegistry for resolving handle references
        """
        self.registry = registry
    
    def parse(self, params: Optional[Dict[str, Any]], 
              param_defs: Optional[List[ParamDef]] = None) -> ParsedParams:
        """
        Parse parameters and convert types.
        
        Args:
            params: Dictionary of parameter name to value
            param_defs: Optional list of parameter definitions for validation
            
        Returns:
            ParsedParams with parsed values
        """
        if params is None:
            params = {}
        
        errors: List[str] = []
        parsed_keyword: Dict[str, Any] = {}
        parsed_positional: List[Any] = []
        
        for name, value in params.items():
            try:
                # Check if value is a handle reference
                if self._is_handle_reference(value):
                    resolved = self._resolve_handle(value)
                    if resolved is None:
                        errors.append(f"Handle not found: {value}")
                        continue
                    value = resolved
                
                # Find param definition if available
                param_def = None
                if param_defs:
                    param_def = next((p for p in param_defs if p.name == name), None)
                
                # Convert type if needed
                if param_def and param_def.param_type:
                    value = self._convert_type(value, param_def.param_type)
                else:
                    # Auto-convert common types
                    value = self._auto_convert(value)
                
                parsed_keyword[name] = value
                
            except Exception as e:
                errors.append(f"Error parsing parameter '{name}': {str(e)}")
        
        return ParsedParams(
            positional=parsed_positional,
            keyword=parsed_keyword,
            errors=errors
        )
    
    def resolve_handles(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve all handle references in parameters.
        
        Args:
            params: Dictionary of parameters
            
        Returns:
            Dictionary with handles resolved to objects
        """
        resolved = {}
        for name, value in params.items():
            if self._is_handle_reference(value):
                obj = self._resolve_handle(value)
                if obj is not None:
                    resolved[name] = obj
                else:
                    resolved[name] = value  # Keep original if not found
            elif isinstance(value, dict):
                # Recursively resolve nested dicts
                resolved[name] = self.resolve_handles(value)
            elif isinstance(value, list):
                # Resolve handles in lists
                resolved[name] = [
                    self._resolve_handle(v) if self._is_handle_reference(v) else v
                    for v in value
                ]
            else:
                resolved[name] = value
        return resolved
    
    def _is_handle_reference(self, value: Any) -> bool:
        """Check if a value is a handle reference."""
        if not isinstance(value, str):
            return False
        # Handle format: type_uuid_timestamp or starts with $
        if value.startswith('$'):
            return True
        # Check for handle pattern
        return bool(re.match(r'^[a-z]+_[a-f0-9]+_\d+$', value))
    
    def _resolve_handle(self, handle_ref: str) -> Optional[Any]:
        """Resolve a handle reference to its object."""
        if not self.registry:
            return None
        
        # Strip $ prefix if present
        handle_id = handle_ref.lstrip('$')
        return self.registry.get(handle_id)
    
    def _convert_type(self, value: Any, target_type: str) -> Any:
        """Convert value to target type."""
        target_lower = target_type.lower().strip()
        
        # Check for KLayout types (pass through)
        if target_lower.startswith('const '):
            target_lower = target_lower[6:]
        
        # Remove ptr suffix
        if target_lower.endswith(' ptr'):
            target_lower = target_lower[:-4]
        
        # Get converter
        converter = self.TYPE_CONVERTERS.get(target_lower)
        if converter:
            return converter(value)
        
        # For complex types, return as-is
        return value
    
    def _auto_convert(self, value: Any) -> Any:
        """Auto-convert string values to appropriate types."""
        if not isinstance(value, str):
            return value
        
        # Try integer
        if re.match(r'^-?\d+$', value):
            return int(value)
        
        # Try float
        if re.match(r'^-?\d+\.?\d*$', value):
            return float(value)
        
        # Try boolean
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        return value
    
    def parse_signature(self, signature: str) -> Tuple[str, List[ParamDef]]:
        """
        Parse a method signature to extract parameter definitions.
        
        Args:
            signature: Method signature string (e.g., "int area(int x, int y)")
            
        Returns:
            Tuple of (return_type, list of ParamDef)
        """
        param_defs: List[ParamDef] = []
        
        # Extract return type and params
        match = re.match(r'([^(]+?)\s+(\w+)\s*\(([^)]*)\)', signature)
        if not match:
            return ('void', [])
        
        return_type = match.group(1).strip()
        params_str = match.group(3).strip()
        
        if not params_str:
            return (return_type, [])
        
        # Parse each parameter
        for param in params_str.split(','):
            param = param.strip()
            if not param:
                continue
            
            # Check for default value
            default_value = None
            is_optional = False
            if '=' in param:
                param, default_str = param.split('=', 1)
                default_value = default_str.strip()
                is_optional = True
            
            # Extract type and name
            parts = param.strip().split()
            if len(parts) >= 2:
                param_type = ' '.join(parts[:-1])
                param_name = parts[-1]
            else:
                param_type = 'unknown'
                param_name = parts[0] if parts else 'arg'
            
            param_defs.append(ParamDef(
                name=param_name,
                param_type=param_type,
                default_value=default_value,
                is_optional=is_optional
            ))
        
        return (return_type, param_defs)
    
    def validate_params(self, params: Dict[str, Any], 
                       param_defs: List[ParamDef]) -> List[str]:
        """
        Validate parameters against definitions.
        
        Args:
            params: Parameters to validate
            param_defs: Expected parameter definitions
            
        Returns:
            List of validation error messages
        """
        errors: List[str] = []
        
        # Check for missing required parameters
        for pdef in param_defs:
            if not pdef.is_optional and pdef.name not in params:
                errors.append(f"Missing required parameter: {pdef.name}")
        
        # Check for unknown parameters
        known_names = {p.name for p in param_defs}
        for name in params:
            if name not in known_names:
                errors.append(f"Unknown parameter: {name}")
        
        return errors
