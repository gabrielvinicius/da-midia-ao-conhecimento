"""
Validation Decorator for automatic input/output validation
"""
import inspect
from typing import Any, Optional, Callable, Dict, Type, get_type_hints
from uuid import UUID
from .base_decorator import BaseAsyncDecorator


class ValidationError(Exception):
    """Custom exception for validation errors"""
    
    def __init__(self, message: str, field: str = None, value: Any = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(message)


class ValidatorRegistry:
    """Registry for custom validators - Registry Pattern"""
    
    _validators: Dict[Type, Callable[[Any], bool]] = {}
    _error_messages: Dict[Type, str] = {}
    
    @classmethod
    def register_validator(
        cls, 
        type_: Type, 
        validator: Callable[[Any], bool], 
        error_message: str = None
    ):
        """Register a custom validator for a type"""
        cls._validators[type_] = validator
        if error_message:
            cls._error_messages[type_] = error_message
    
    @classmethod
    def get_validator(cls, type_: Type) -> Optional[Callable[[Any], bool]]:
        """Get validator for a type"""
        return cls._validators.get(type_)
    
    @classmethod
    def get_error_message(cls, type_: Type) -> str:
        """Get error message for a type"""
        return cls._error_messages.get(type_, f"Invalid value for type {type_.__name__}")


class ValidationDecorator(BaseAsyncDecorator):
    """Decorator for automatic input/output validation"""
    
    def __init__(
        self,
        validate_inputs: bool = True,
        validate_outputs: bool = False,
        strict_typing: bool = False,
        custom_validators: Dict[str, Callable] = None
    ):
        super().__init__("validation")
        self.validate_inputs = validate_inputs
        self.validate_outputs = validate_outputs
        self.strict_typing = strict_typing
        self.custom_validators = custom_validators or {}
        self.function_signature = None
        self.return_type = None
    
    def decorate(self, func: Callable) -> Callable:
        """Enhanced decoration with signature analysis"""
        # Analyze function signature for validation
        self.function_signature = inspect.signature(func)
        
        # Get type hints for validation
        try:
            type_hints = get_type_hints(func)
            self.return_type = type_hints.get('return')
        except:
            # If type hints analysis fails, continue without strict typing
            self.strict_typing = False
        
        return super().decorate(func)
    
    async def _before_execution(self, *args, **kwargs) -> Optional[Any]:
        """Validate inputs before execution"""
        if self.validate_inputs:
            self._validate_function_inputs(*args, **kwargs)
        return None
    
    async def _after_execution(self, result: Any, *args, **kwargs) -> Any:
        """Validate outputs after execution"""
        if self.validate_outputs:
            self._validate_function_output(result)
        return result
    
    async def _on_exception(self, exception: Exception, *args, **kwargs) -> None:
        """Handle validation exceptions"""
        if isinstance(exception, ValidationError):
            # Re-raise validation errors with enhanced context
            raise ValidationError(
                f"Validation failed: {exception.message}",
                exception.field,
                exception.value
            ) from exception
    
    def _validate_function_inputs(self, *args, **kwargs) -> None:
        """Validate function input parameters"""
        if not self.function_signature:
            return
        
        # Bind arguments to parameters
        try:
            bound_args = self.function_signature.bind(*args, **kwargs)
            bound_args.apply_defaults()
        except TypeError as e:
            raise ValidationError(f"Invalid function arguments: {e}")
        
        # Validate each parameter
        for param_name, value in bound_args.arguments.items():
            self._validate_parameter(param_name, value)
    
    def _validate_parameter(self, param_name: str, value: Any) -> None:
        """Validate individual parameter"""
        # Skip self parameter
        if param_name == 'self':
            return
        
        # Get parameter info
        param = self.function_signature.parameters.get(param_name)
        if not param:
            return
        
        # Custom validator check
        if param_name in self.custom_validators:
            validator = self.custom_validators[param_name]
            if not validator(value):
                raise ValidationError(
                    f"Custom validation failed for parameter '{param_name}'",
                    param_name,
                    value
                )
        
        # Type annotation validation
        if self.strict_typing and param.annotation != inspect.Parameter.empty:
            self._validate_type(param_name, value, param.annotation)
        
        # Common validations
        self._validate_common_constraints(param_name, value)
    
    def _validate_type(self, param_name: str, value: Any, expected_type: Type) -> None:
        """Validate parameter type"""
        if value is None:
            # Allow None for Optional types
            return
        
        # Handle basic type validation
        if not isinstance(value, expected_type):
            # Check for registered custom validator
            validator = ValidatorRegistry.get_validator(expected_type)
            if validator and validator(value):
                return
            
            raise ValidationError(
                f"Parameter '{param_name}' must be of type {expected_type.__name__}, got {type(value).__name__}",
                param_name,
                value
            )
    
    def _validate_common_constraints(self, param_name: str, value: Any) -> None:
        """Apply common validation constraints"""
        
        # String validations
        if isinstance(value, str):
            if len(value.strip()) == 0 and param_name not in ['description', 'comment', 'note']:
                raise ValidationError(
                    f"Parameter '{param_name}' cannot be empty string",
                    param_name,
                    value
                )
            
            if len(value) > 10000:  # Prevent extremely long strings
                raise ValidationError(
                    f"Parameter '{param_name}' exceeds maximum length (10000 characters)",
                    param_name,
                    value
                )
        
        # UUID validations
        if param_name.endswith('_id') and isinstance(value, str):
            try:
                UUID(value)
            except ValueError:
                raise ValidationError(
                    f"Parameter '{param_name}' must be a valid UUID",
                    param_name,
                    value
                )
        
        # Collection validations
        if isinstance(value, (list, tuple, dict)):
            if len(value) > 1000:  # Prevent extremely large collections
                raise ValidationError(
                    f"Parameter '{param_name}' exceeds maximum size (1000 items)",
                    param_name,
                    value
                )
        
        # Numeric validations
        if isinstance(value, (int, float)):
            if param_name.endswith('_count') and value < 0:
                raise ValidationError(
                    f"Parameter '{param_name}' cannot be negative",
                    param_name,
                    value
                )
    
    def _validate_function_output(self, result: Any) -> None:
        """Validate function output"""
        if result is None:
            return
        
        # Type validation for return value
        if self.strict_typing and self.return_type:
            if not isinstance(result, self.return_type):
                raise ValidationError(
                    f"Return value must be of type {self.return_type.__name__}, got {type(result).__name__}",
                    "return_value",
                    result
                )


class BusinessValidationDecorator(ValidationDecorator):
    """Specialized decorator for business rule validation"""
    
    def __init__(self, business_rules: Dict[str, Callable] = None):
        super().__init__(validate_inputs=True, validate_outputs=False)
        self.business_rules = business_rules or {}
    
    async def _before_execution(self, *args, **kwargs) -> Optional[Any]:
        """Apply business rule validations"""
        # Standard input validation
        await super()._before_execution(*args, **kwargs)
        
        # Apply business rules
        for rule_name, rule_validator in self.business_rules.items():
            try:
                if not rule_validator(*args, **kwargs):
                    raise ValidationError(f"Business rule '{rule_name}' validation failed")
            except Exception as e:
                if isinstance(e, ValidationError):
                    raise
                raise ValidationError(f"Business rule '{rule_name}' validation error: {e}")
        
        return None


# Register common validators
ValidatorRegistry.register_validator(
    UUID,
    lambda x: isinstance(x, (UUID, str)) and (isinstance(x, UUID) or UUID(x)),
    "Must be a valid UUID"
)

ValidatorRegistry.register_validator(
    bytes,
    lambda x: isinstance(x, (bytes, bytearray)),
    "Must be bytes or bytearray"
)