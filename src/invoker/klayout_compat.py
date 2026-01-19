"""
KLayout Module Compatibility Layer

This module provides a unified interface for importing KLayout Python API,
supporting both 'pya' (inside KLayout GUI) and 'klayout.db' (standalone) modes.

According to KLayout documentation:
- Inside KLayout GUI: use 'import pya'
- Standalone Python: use 'import klayout.db', 'import klayout.lay', etc.

This compatibility layer automatically detects the environment and provides
a unified interface.
"""

import importlib
import sys
from typing import Any, Dict, Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class KLayoutModuleInfo:
    """Information about a loaded KLayout module."""
    name: str           # Short name (db, lay, tl, rdb, lib)
    full_path: str      # Full import path
    module: Any         # Actual module object
    mode: str           # 'pya' or 'standalone'


class KLayoutCompat:
    """
    KLayout module compatibility layer.
    
    Provides unified access to KLayout Python API regardless of whether
    the code is running inside KLayout GUI or as a standalone Python program.
    """
    
    # Module name mappings for standalone mode
    STANDALONE_MODULES = {
        'db': 'klayout.db',
        'lay': 'klayout.lay',
        'rdb': 'klayout.rdb',
        'tl': 'klayout.tl',
        'lib': 'klayout.lib',
    }
    
    # Common classes and their modules
    CLASS_MODULE_MAP = {
        # db module classes
        'Layout': 'db', 'Cell': 'db', 'Instance': 'db',
        'Box': 'db', 'DBox': 'db', 'Point': 'db', 'DPoint': 'db',
        'Vector': 'db', 'DVector': 'db',
        'Edge': 'db', 'DEdge': 'db', 'EdgePair': 'db', 'DEdgePair': 'db',
        'Path': 'db', 'DPath': 'db', 'Polygon': 'db', 'DPolygon': 'db',
        'SimplePolygon': 'db', 'DSimplePolygon': 'db',
        'Text': 'db', 'DText': 'db',
        'Region': 'db', 'Edges': 'db', 'EdgePairs': 'db', 'Texts': 'db',
        'Trans': 'db', 'DTrans': 'db', 'CplxTrans': 'db', 'DCplxTrans': 'db',
        'ICplxTrans': 'db', 'VCplxTrans': 'db',
        'LayerInfo': 'db', 'RecursiveShapeIterator': 'db', 'Shapes': 'db',
        'RecursiveInstanceIterator': 'db', 'ShapeProcessor': 'db',
        'Technology': 'db', 'Library': 'db', 'PCellDeclaration': 'db',
        'LayoutMetaInfo': 'db', 'CellInstArray': 'db',
        'LayerMapping': 'db', 'SaveLayoutOptions': 'db', 'LoadLayoutOptions': 'db',
        
        # lay module classes (GUI related)
        'LayoutView': 'lay', 'LayerProperties': 'lay', 'CellView': 'lay',
        'Application': 'lay', 'MainWindow': 'lay', 'Annotation': 'lay',
        'Marker': 'lay', 'Image': 'lay', 'LayoutViewBase': 'lay',
        'PixelBuffer': 'lay', 'BitmapBuffer': 'lay',
        'LayoutToNetlist': 'lay', 'NetlistSpiceReader': 'lay',
        
        # tl module classes (tool/utility)
        'Progress': 'tl', 'AbsoluteProgress': 'tl', 'RelativeProgress': 'tl',
        'Logger': 'tl', 'Timer': 'tl', 'Expression': 'tl',
        'GlobPattern': 'tl', 'Variant': 'tl',
        
        # rdb module classes (report database)
        'ReportDatabase': 'rdb', 'RdbCategory': 'rdb', 'RdbItem': 'rdb',
        'RdbCell': 'rdb', 'RdbReference': 'rdb', 'RdbItemValue': 'rdb',
    }
    
    def __init__(self):
        """Initialize the compatibility layer."""
        self._mode: Optional[str] = None  # 'pya' or 'standalone'
        self._pya_module: Optional[Any] = None
        self._module_cache: Dict[str, KLayoutModuleInfo] = {}
        self._initialized = False
        
    def initialize(self) -> bool:
        """
        Initialize and detect the KLayout environment.
        
        Returns:
            True if KLayout modules are available
        """
        if self._initialized:
            return self._mode is not None
        
        self._initialized = True
        
        # First, try to import 'pya' (available inside KLayout GUI)
        # But verify it actually has KLayout classes (not just a stub module)
        try:
            import pya
            # Verify pya has actual KLayout classes (Box is a good test)
            if hasattr(pya, 'Box'):
                self._mode = 'pya'
                self._pya_module = pya
                
                # In pya mode, all classes are in the pya module
                for mod_name in self.STANDALONE_MODULES:
                    self._module_cache[mod_name] = KLayoutModuleInfo(
                        name=mod_name,
                        full_path='pya',
                        module=pya,
                        mode='pya'
                    )
                return True
            # pya exists but doesn't have KLayout classes, fall through to standalone
        except ImportError:
            pass
        
        # Second, try standalone klayout modules
        try:
            import klayout.db as db
            self._mode = 'standalone'
            
            # Load all available modules
            for mod_name, mod_path in self.STANDALONE_MODULES.items():
                try:
                    mod = importlib.import_module(mod_path)
                    self._module_cache[mod_name] = KLayoutModuleInfo(
                        name=mod_name,
                        full_path=mod_path,
                        module=mod,
                        mode='standalone'
                    )
                except ImportError:
                    # Some modules may not be available (e.g., lay without Qt)
                    pass
            
            return True
        except ImportError:
            pass
        
        # Neither mode is available
        self._mode = None
        return False
    
    @property
    def mode(self) -> Optional[str]:
        """Get the current mode ('pya' or 'standalone')."""
        if not self._initialized:
            self.initialize()
        return self._mode
    
    @property
    def is_available(self) -> bool:
        """Check if KLayout modules are available."""
        if not self._initialized:
            self.initialize()
        return self._mode is not None
    
    def get_module(self, module_name: str) -> Optional[Any]:
        """
        Get a KLayout module by name.
        
        Args:
            module_name: Short module name (db, lay, tl, rdb, lib)
            
        Returns:
            The module object or None if not available
        """
        if not self._initialized:
            self.initialize()
        
        info = self._module_cache.get(module_name)
        return info.module if info else None
    
    def get_class(self, class_name: str, module_name: Optional[str] = None) -> Optional[type]:
        """
        Get a class from KLayout modules.
        
        Args:
            class_name: Name of the class (e.g., 'Box', 'Layout')
            module_name: Optional module name hint
            
        Returns:
            The class or None if not found
        """
        if not self._initialized:
            self.initialize()
        
        if not self._mode:
            return None
        
        # Determine which module to look in
        if module_name is None:
            module_name = self.CLASS_MODULE_MAP.get(class_name, 'db')
        
        module = self.get_module(module_name)
        if module is None:
            # Fallback: try other modules
            for mod_name, mod_info in self._module_cache.items():
                cls = getattr(mod_info.module, class_name, None)
                if cls is not None:
                    return cls
            return None
        
        return getattr(module, class_name, None)
    
    def get_module_for_class(self, class_name: str) -> str:
        """
        Get the module name for a given class.
        
        Args:
            class_name: Name of the class
            
        Returns:
            Module name (defaults to 'db' if unknown)
        """
        return self.CLASS_MODULE_MAP.get(class_name, 'db')
    
    def create_instance(self, class_name: str, *args, 
                       module_name: Optional[str] = None,
                       **kwargs) -> Tuple[Optional[Any], Optional[str]]:
        """
        Create an instance of a KLayout class.
        
        Args:
            class_name: Name of the class
            *args: Positional arguments for constructor
            module_name: Optional module name hint
            **kwargs: Keyword arguments for constructor
            
        Returns:
            Tuple of (instance, error_message)
        """
        cls = self.get_class(class_name, module_name)
        if cls is None:
            return None, f"Class not found: {class_name}"
        
        try:
            if args and kwargs:
                instance = cls(*args, **kwargs)
            elif args:
                instance = cls(*args)
            elif kwargs:
                instance = cls(**kwargs)
            else:
                instance = cls()
            return instance, None
        except Exception as e:
            return None, f"Error creating {class_name}: {str(e)}"
    
    def is_klayout_object(self, obj: Any) -> bool:
        """
        Check if an object is a KLayout object.
        
        Args:
            obj: Object to check
            
        Returns:
            True if the object is from KLayout modules
        """
        if obj is None:
            return False
        
        obj_module = type(obj).__module__
        
        # Check pya mode
        if obj_module == 'pya':
            return True
        
        # Check standalone mode
        if obj_module.startswith('klayout.'):
            return True
        
        return False
    
    def get_object_module(self, obj: Any) -> Optional[str]:
        """
        Get the module name for a KLayout object.
        
        Args:
            obj: KLayout object
            
        Returns:
            Module name (db, lay, etc.) or None
        """
        if not self.is_klayout_object(obj):
            return None
        
        obj_module = type(obj).__module__
        
        if obj_module == 'pya':
            # In pya mode, guess from class name
            return self.CLASS_MODULE_MAP.get(type(obj).__name__, 'db')
        
        # In standalone mode, extract from module path
        for mod_name, mod_path in self.STANDALONE_MODULES.items():
            if obj_module == mod_path:
                return mod_name
        
        return 'db'
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the compatibility layer.
        
        Returns:
            Dictionary with status information
        """
        if not self._initialized:
            self.initialize()
        
        return {
            "initialized": self._initialized,
            "mode": self._mode,
            "available": self.is_available,
            "modules_loaded": list(self._module_cache.keys()),
            "pya_available": self._pya_module is not None,
        }


# Global singleton instance
_klayout_compat: Optional[KLayoutCompat] = None


def get_klayout_compat() -> KLayoutCompat:
    """Get the global KLayoutCompat singleton instance."""
    global _klayout_compat
    if _klayout_compat is None:
        _klayout_compat = KLayoutCompat()
    return _klayout_compat


def reset_klayout_compat() -> None:
    """Reset the global KLayoutCompat singleton (useful for testing)."""
    global _klayout_compat
    _klayout_compat = None


def get_pya() -> Optional[Any]:
    """
    Get the pya-compatible module.
    
    Returns the pya module in GUI mode, or the db module in standalone mode.
    This provides backward compatibility for code written for pya.
    """
    compat = get_klayout_compat()
    if compat.mode == 'pya':
        return compat._pya_module
    else:
        return compat.get_module('db')


def import_klayout_class(class_name: str) -> Optional[type]:
    """
    Import a KLayout class by name.
    
    Args:
        class_name: Name of the class
        
    Returns:
        The class or None if not found
    """
    return get_klayout_compat().get_class(class_name)
