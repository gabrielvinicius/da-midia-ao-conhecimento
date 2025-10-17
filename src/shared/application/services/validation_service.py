# src/shared/application/services/validation_service.py
"""
Validation Service implementation following SRP principle.
Responsible only for data validation operations.
"""
import re
import html
import structlog
from typing import Dict, Any, List
from email_validator import validate_email as email_validate, EmailNotValidError

from src.shared.domain.interfaces import ValidationService as IValidationService

logger = structlog.get_logger(__name__)


class ValidationService(IValidationService):
    """
    Data validation service implementation.
    Follows SRP: Only responsible for validation and sanitization operations.
    """
    
    def validate_email(self, email: str) -> bool:
        """Validate email format."""
        if not email:
            return False
        
        try:
            # Use email-validator library for comprehensive validation
            email_validate(email)
            return True
        except EmailNotValidError:
            return False
        except Exception as e:
            logger.warning("email.validation.error", email=email, error=str(e))
            return False
    
    def validate_data(self, data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, List[str]]:
        """Validate data against schema, return errors."""
        errors = {}
        
        logger.debug("data.validation.started", schema_fields=list(schema.keys()))
        
        try:
            for field, rules in schema.items():
                field_errors = []
                value = data.get(field)
                
                # Required validation
                if rules.get('required', False) and (value is None or value == ''):
                    field_errors.append(f"{field} is required")
                    continue
                
                # Skip further validation if field is optional and empty
                if value is None or value == '':
                    continue
                
                # Type validation
                expected_type = rules.get('type')
                if expected_type and not isinstance(value, expected_type):
                    field_errors.append(f"{field} must be of type {expected_type.__name__}")
                    continue
                
                # String validations
                if isinstance(value, str):
                    field_errors.extend(self._validate_string_rules(field, value, rules))
                
                # Numeric validations
                if isinstance(value, (int, float)):
                    field_errors.extend(self._validate_numeric_rules(field, value, rules))
                
                # Custom validation
                custom_validator = rules.get('validator')
                if custom_validator and callable(custom_validator):
                    try:
                        if not custom_validator(value):
                            field_errors.append(f"{field} failed custom validation")
                    except Exception as e:
                        field_errors.append(f"{field} validation error: {str(e)}")
                
                if field_errors:
                    errors[field] = field_errors
            
            logger.debug("data.validation.completed", errors_count=len(errors))
            return errors
            
        except Exception as e:
            logger.error("data.validation.failed", error=str(e))
            return {"validation": ["Validation failed due to internal error"]}
    
    def sanitize_input(self, input_data: str) -> str:
        """Sanitize user input."""
        if not isinstance(input_data, str):
            return str(input_data)
        
        logger.debug("input.sanitization.started", length=len(input_data))
        
        try:
            # HTML escape
            sanitized = html.escape(input_data)
            
            # Remove null bytes
            sanitized = sanitized.replace('\x00', '')
            
            # Normalize whitespace
            sanitized = re.sub(r'\s+', ' ', sanitized).strip()
            
            logger.debug("input.sanitization.completed", 
                        original_length=len(input_data),
                        sanitized_length=len(sanitized))
            
            return sanitized
            
        except Exception as e:
            logger.error("input.sanitization.failed", error=str(e))
            return ""
    
    def _validate_string_rules(self, field: str, value: str, rules: Dict[str, Any]) -> List[str]:
        """Validate string-specific rules."""
        errors = []
        
        # Length validations
        min_length = rules.get('min_length')
        if min_length and len(value) < min_length:
            errors.append(f"{field} must be at least {min_length} characters long")
        
        max_length = rules.get('max_length')
        if max_length and len(value) > max_length:
            errors.append(f"{field} must not exceed {max_length} characters")
        
        # Pattern validation
        pattern = rules.get('pattern')
        if pattern and not re.match(pattern, value):
            errors.append(f"{field} format is invalid")
        
        # Email validation
        if rules.get('email', False) and not self.validate_email(value):
            errors.append(f"{field} must be a valid email address")
        
        return errors
    
    def _validate_numeric_rules(self, field: str, value: float, rules: Dict[str, Any]) -> List[str]:
        """Validate numeric-specific rules."""
        errors = []
        
        # Range validations
        min_value = rules.get('min_value')
        if min_value is not None and value < min_value:
            errors.append(f"{field} must be at least {min_value}")
        
        max_value = rules.get('max_value')
        if max_value is not None and value > max_value:
            errors.append(f"{field} must not exceed {max_value}")
        
        return errors
    
    def validate_uuid(self, uuid_string: str) -> bool:
        """Validate UUID format."""
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        return bool(uuid_pattern.match(uuid_string))
    
    def validate_phone(self, phone: str) -> bool:
        """Validate phone number format."""
        # Simple phone validation - can be enhanced for international formats
        phone_pattern = re.compile(r'^\+?[\d\s\-\(\)]{10,}$')
        return bool(phone_pattern.match(phone))
    
    def validate_url(self, url: str) -> bool:
        """Validate URL format."""
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return bool(url_pattern.match(url))