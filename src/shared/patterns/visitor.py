"""
Visitor Pattern implementation for extensible operations on object structures
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic, Type
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')  # Element type
R = TypeVar('R')  # Result type


class VisitorResult:
    """Container for visitor operation results"""
    
    def __init__(self, success: bool = True):
        self.success = success
        self.results: Dict[str, Any] = {}
        self.errors: List[str] = []
        self.metadata: Dict[str, Any] = {}
        self.visited_count = 0
    
    def add_result(self, key: str, value: Any) -> None:
        """Add result for specific operation"""
        self.results[key] = value
    
    def add_error(self, error: str) -> None:
        """Add error to result"""
        self.errors.append(error)
        self.success = False
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata"""
        self.metadata[key] = value
    
    def increment_visited(self) -> None:
        """Increment visited elements counter"""
        self.visited_count += 1
    
    def get_result(self, key: str, default: Any = None) -> Any:
        """Get specific result"""
        return self.results.get(key, default)
    
    def has_errors(self) -> bool:
        """Check if there are errors"""
        return len(self.errors) > 0


class IVisitable(ABC):
    """Interface for objects that can be visited"""
    
    @abstractmethod
    def accept(self, visitor: 'IVisitor') -> Any:
        """Accept a visitor and delegate the operation"""
        pass
    
    def get_element_type(self) -> str:
        """Get element type for visitor dispatch"""
        return self.__class__.__name__


class IVisitor(ABC, Generic[R]):
    """Base interface for all visitors"""
    
    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
        self.result = VisitorResult()
    
    def visit(self, element: IVisitable) -> R:
        """Visit an element and perform operation"""
        
        logger.debug(
            f"Visitor {self.name} visiting {element.get_element_type()}",
            extra={
                "visitor": self.name,
                "element_type": element.get_element_type()
            }
        )
        
        try:
            # Increment visited counter
            self.result.increment_visited()
            
            # Delegate to element's accept method
            return element.accept(self)
            
        except Exception as e:
            error_msg = f"Error visiting {element.get_element_type()}: {str(e)}"
            self.result.add_error(error_msg)
            
            logger.error(
                f"Visitor {self.name} failed",
                extra={
                    "visitor": self.name,
                    "element_type": element.get_element_type(),
                    "error": str(e)
                },
                exc_info=True
            )
            
            return self._handle_visit_error(element, e)
    
    @abstractmethod
    def _handle_visit_error(self, element: IVisitable, error: Exception) -> R:
        """Handle errors during visitation"""
        pass
    
    def get_results(self) -> VisitorResult:
        """Get visitor results"""
        return self.result
    
    def reset(self) -> None:
        """Reset visitor state for reuse"""
        self.result = VisitorResult()


class BaseVisitor(IVisitor[R]):
    """Base implementation of visitor with common functionality"""
    
    def __init__(self, name: str = None, collect_metadata: bool = True):
        super().__init__(name)
        self.collect_metadata = collect_metadata
        self._dispatch_table: Dict[str, callable] = {}
        self._build_dispatch_table()
    
    def _build_dispatch_table(self) -> None:
        """Build dispatch table for visitor methods"""
        
        # Find all visit_* methods in the class
        for attr_name in dir(self):
            if attr_name.startswith('visit_') and callable(getattr(self, attr_name)):
                element_type = attr_name[6:]  # Remove 'visit_' prefix
                self._dispatch_table[element_type] = getattr(self, attr_name)
    
    def visit(self, element: IVisitable) -> R:
        """Enhanced visit with dispatch table"""
        
        if self.collect_metadata:
            self.result.add_metadata(f"visited_{element.get_element_type()}", True)
        
        return super().visit(element)
    
    def dispatch(self, element: IVisitable) -> R:
        """Dispatch to appropriate visit method"""
        
        element_type = element.get_element_type()
        
        # Try exact match first
        if element_type in self._dispatch_table:
            return self._dispatch_table[element_type](element)
        
        # Try base class matches
        for registered_type, method in self._dispatch_table.items():
            if registered_type in element_type or element_type.endswith(registered_type):
                return method(element)
        
        # Fall back to default visit method
        return self.visit_default(element)
    
    def visit_default(self, element: IVisitable) -> R:
        """Default visit method for unhandled element types"""
        logger.warning(
            f"No specific visit method for {element.get_element_type()}",
            extra={
                "visitor": self.name,
                "element_type": element.get_element_type()
            }
        )
        return self._create_default_result(element)
    
    @abstractmethod
    def _create_default_result(self, element: IVisitable) -> R:
        """Create default result for unhandled elements"""
        pass
    
    def _handle_visit_error(self, element: IVisitable, error: Exception) -> R:
        """Default error handling"""
        return self._create_default_result(element)


class CompositeElement(IVisitable):
    """Base class for composite elements that contain other visitable elements"""
    
    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
        self.children: List[IVisitable] = []
    
    def add_child(self, child: IVisitable) -> None:
        """Add child element"""
        self.children.append(child)
    
    def remove_child(self, child: IVisitable) -> None:
        """Remove child element"""
        if child in self.children:
            self.children.remove(child)
    
    def get_children(self) -> List[IVisitable]:
        """Get all child elements"""
        return self.children.copy()
    
    def accept(self, visitor: IVisitor) -> Any:
        """Accept visitor and visit all children"""
        
        # Visit this element
        result = visitor.dispatch(self)
        
        # Visit all children
        child_results = []
        for child in self.children:
            child_result = child.accept(visitor)
            child_results.append(child_result)
        
        # Combine results if needed
        return self._combine_results(result, child_results)
    
    def _combine_results(self, self_result: Any, child_results: List[Any]) -> Any:
        """Combine this element's result with children results"""
        return {
            "self": self_result,
            "children": child_results
        }


class LeafElement(IVisitable):
    """Base class for leaf elements (no children)"""
    
    def __init__(self, name: str = None, data: Any = None):
        self.name = name or self.__class__.__name__
        self.data = data
    
    def accept(self, visitor: IVisitor) -> Any:
        """Accept visitor"""
        return visitor.dispatch(self)


class VisitorChain:
    """Chain multiple visitors to execute in sequence"""
    
    def __init__(self, visitors: List[IVisitor]):
        self.visitors = visitors
        self.results: List[VisitorResult] = []
    
    def visit_element(self, element: IVisitable) -> Dict[str, Any]:
        """Visit element with all visitors in the chain"""
        
        combined_results = {}
        self.results.clear()
        
        for visitor in self.visitors:
            try:
                # Reset visitor for clean state
                visitor.reset()
                
                # Visit element
                result = visitor.visit(element)
                
                # Store results
                visitor_result = visitor.get_results()
                self.results.append(visitor_result)
                combined_results[visitor.name] = {
                    "result": result,
                    "metadata": visitor_result.metadata,
                    "visited_count": visitor_result.visited_count,
                    "errors": visitor_result.errors
                }
                
            except Exception as e:
                error_result = VisitorResult(False)
                error_result.add_error(f"Visitor {visitor.name} failed: {str(e)}")
                self.results.append(error_result)
                combined_results[visitor.name] = {
                    "result": None,
                    "error": str(e)
                }
        
        return combined_results
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all visitor results"""
        
        total_visited = sum(r.visited_count for r in self.results)
        total_errors = sum(len(r.errors) for r in self.results)
        successful_visitors = sum(1 for r in self.results if r.success)
        
        return {
            "total_visitors": len(self.visitors),
            "successful_visitors": successful_visitors,
            "total_elements_visited": total_visited,
            "total_errors": total_errors,
            "success_rate": (successful_visitors / len(self.visitors) * 100) if self.visitors else 0
        }


class ConditionalVisitor(BaseVisitor[R]):
    """Visitor that applies conditions before visiting elements"""
    
    def __init__(self, base_visitor: IVisitor, condition: callable, name: str = None):
        super().__init__(name or f"Conditional{base_visitor.name}")
        self.base_visitor = base_visitor
        self.condition = condition
        self.skipped_count = 0
    
    def visit(self, element: IVisitable) -> R:
        """Visit element only if condition is met"""
        
        if self.condition(element):
            return self.base_visitor.visit(element)
        else:
            self.skipped_count += 1
            self.result.add_metadata("skipped_elements", self.skipped_count)
            return self._create_skipped_result(element)
    
    def dispatch(self, element: IVisitable) -> R:
        """Dispatch with condition check"""
        if self.condition(element):
            return self.base_visitor.dispatch(element)
        else:
            self.skipped_count += 1
            return self._create_skipped_result(element)
    
    def _create_skipped_result(self, element: IVisitable) -> R:
        """Create result for skipped elements"""
        return None
    
    def _create_default_result(self, element: IVisitable) -> R:
        """Default result for conditional visitor"""
        return None
    
    def get_results(self) -> VisitorResult:
        """Get results including base visitor results"""
        combined_result = self.result
        base_result = self.base_visitor.get_results()
        
        # Merge results
        combined_result.results.update(base_result.results)
        combined_result.errors.extend(base_result.errors)
        combined_result.metadata.update(base_result.metadata)
        combined_result.visited_count += base_result.visited_count
        
        return combined_result


class VisitorRegistry:
    """Registry for managing and organizing visitors"""
    
    _visitors: Dict[str, Type[IVisitor]] = {}
    _categories: Dict[str, List[str]] = {}
    
    @classmethod
    def register_visitor(cls, name: str, visitor_class: Type[IVisitor], category: str = "general"):
        """Register a visitor class"""
        cls._visitors[name] = visitor_class
        
        if category not in cls._categories:
            cls._categories[category] = []
        cls._categories[category].append(name)
        
        logger.info(f"Registered visitor: {name} in category: {category}")
    
    @classmethod
    def create_visitor(cls, name: str, **kwargs) -> IVisitor:
        """Create visitor instance"""
        visitor_class = cls._visitors.get(name)
        if not visitor_class:
            raise ValueError(f"Visitor '{name}' not found in registry")
        
        return visitor_class(**kwargs)
    
    @classmethod
    def get_visitors_by_category(cls, category: str) -> List[str]:
        """Get all visitors in a category"""
        return cls._categories.get(category, [])
    
    @classmethod
    def get_all_visitors(cls) -> Dict[str, str]:
        """Get all registered visitors with their categories"""
        result = {}
        for category, visitors in cls._categories.items():
            for visitor in visitors:
                result[visitor] = category
        return result
    
    @classmethod
    def create_visitor_chain(cls, visitor_names: List[str], **kwargs) -> VisitorChain:
        """Create a chain of visitors"""
        visitors = []
        for name in visitor_names:
            visitor = cls.create_visitor(name, **kwargs)
            visitors.append(visitor)
        return VisitorChain(visitors)


class AsyncVisitor(IVisitor[R]):
    """Base class for asynchronous visitors"""
    
    async def visit_async(self, element: IVisitable) -> R:
        """Asynchronous visit method"""
        
        logger.debug(
            f"Async visitor {self.name} visiting {element.get_element_type()}",
            extra={
                "visitor": self.name,
                "element_type": element.get_element_type()
            }
        )
        
        try:
            self.result.increment_visited()
            return await element.accept_async(self)
            
        except Exception as e:
            error_msg = f"Error visiting {element.get_element_type()}: {str(e)}"
            self.result.add_error(error_msg)
            
            logger.error(
                f"Async visitor {self.name} failed",
                extra={
                    "visitor": self.name,
                    "element_type": element.get_element_type(),
                    "error": str(e)
                },
                exc_info=True
            )
            
            return await self._handle_visit_error_async(element, e)
    
    @abstractmethod
    async def _handle_visit_error_async(self, element: IVisitable, error: Exception) -> R:
        """Handle errors during async visitation"""
        pass


class AsyncVisitableElement(IVisitable):
    """Base class for elements that support async visitation"""
    
    async def accept_async(self, visitor: AsyncVisitor) -> Any:
        """Accept async visitor"""
        return await visitor.dispatch_async(self)
    
    def accept(self, visitor: IVisitor) -> Any:
        """Synchronous accept for compatibility"""
        if isinstance(visitor, AsyncVisitor):
            # Convert to sync execution
            import asyncio
            return asyncio.run(self.accept_async(visitor))
        else:
            return visitor.dispatch(self)