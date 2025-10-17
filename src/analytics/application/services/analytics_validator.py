"""
Analytics Validator Service - Single Responsibility: Validation operations.
Follows SRP by handling only validation concerns for analytics.
"""
from typing import Dict, Any, Set
import structlog

from src.analytics.domain.interfaces import IAnalyticsValidator, TimeRange, ProcessingType
from src.shared.exceptions.domain_exceptions import ValidationError

logger = structlog.get_logger(__name__)


class AnalyticsValidator(IAnalyticsValidator):
    """
    Validates analytics inputs and parameters following SRP.
    Single responsibility: All validation logic for analytics operations.
    """
    
    def __init__(self):
        self.valid_time_ranges = {tr.value for tr in TimeRange}
        self.valid_processing_types = {pt.value for pt in ProcessingType}
        self.valid_export_formats = {"json", "csv", "xlsx", "pdf"}
    
    def validate_time_range(self, time_range: TimeRange) -> None:
        """
        Validate time range for analytics queries.
        
        Args:
            time_range: Time range to validate
            
        Raises:
            ValidationError: If time range is invalid
        """
        if not isinstance(time_range, TimeRange):
            raise ValidationError("Time range must be a valid TimeRange enum value")
        
        if time_range.value not in self.valid_time_ranges:
            raise ValidationError(
                f"Invalid time range: {time_range.value}. "
                f"Valid options: {', '.join(self.valid_time_ranges)}"
            )
        
        logger.debug(
            "analytics.validation.time_range_validated",
            time_range=time_range.value
        )
    
    def validate_processing_type(self, processing_type: ProcessingType) -> None:
        """
        Validate processing type parameter.
        
        Args:
            processing_type: Processing type to validate
            
        Raises:
            ValidationError: If processing type is invalid
        """
        if not isinstance(processing_type, ProcessingType):
            raise ValidationError("Processing type must be a valid ProcessingType enum value")
        
        if processing_type.value not in self.valid_processing_types:
            raise ValidationError(
                f"Invalid processing type: {processing_type.value}. "
                f"Valid options: {', '.join(self.valid_processing_types)}"
            )
        
        logger.debug(
            "analytics.validation.processing_type_validated",
            processing_type=processing_type.value
        )
    
    def validate_metric_parameters(self, parameters: Dict[str, Any]) -> None:
        """
        Validate metric calculation parameters.
        
        Args:
            parameters: Parameters to validate
            
        Raises:
            ValidationError: If parameters are invalid
        """
        if not isinstance(parameters, dict):
            raise ValidationError("Metric parameters must be a dictionary")
        
        # Validate hours_ahead parameter
        if "hours_ahead" in parameters:
            hours_ahead = parameters["hours_ahead"]
            if not isinstance(hours_ahead, int) or hours_ahead < 1 or hours_ahead > 168:  # Max 1 week
                raise ValidationError("hours_ahead must be an integer between 1 and 168 (1 week)")
        
        # Validate threshold parameters
        if "threshold" in parameters:
            threshold = parameters["threshold"]
            if not isinstance(threshold, (int, float)) or threshold < 0 or threshold > 100:
                raise ValidationError("threshold must be a number between 0 and 100")
        
        # Validate limit parameters
        if "limit" in parameters:
            limit = parameters["limit"]
            if not isinstance(limit, int) or limit < 1 or limit > 1000:
                raise ValidationError("limit must be an integer between 1 and 1000")
        
        # Validate export format
        if "export_format" in parameters:
            export_format = parameters["export_format"]
            if export_format not in self.valid_export_formats:
                raise ValidationError(
                    f"Invalid export format: {export_format}. "
                    f"Valid formats: {', '.join(self.valid_export_formats)}"
                )
        
        # Validate date range parameters
        if "start_date" in parameters and "end_date" in parameters:
            self._validate_date_range(parameters["start_date"], parameters["end_date"])
        
        logger.debug(
            "analytics.validation.parameters_validated",
            parameters=parameters
        )
    
    def validate_aggregation_parameters(self, aggregation_type: str, parameters: Dict[str, Any]) -> None:
        """
        Validate aggregation parameters.
        
        Args:
            aggregation_type: Type of aggregation (sum, avg, count, etc.)
            parameters: Aggregation parameters
            
        Raises:
            ValidationError: If aggregation parameters are invalid
        """
        valid_aggregation_types = {"sum", "avg", "count", "min", "max", "median", "percentile"}
        
        if aggregation_type not in valid_aggregation_types:
            raise ValidationError(
                f"Invalid aggregation type: {aggregation_type}. "
                f"Valid types: {', '.join(valid_aggregation_types)}"
            )
        
        # Validate percentile parameter
        if aggregation_type == "percentile":
            if "percentile" not in parameters:
                raise ValidationError("Percentile aggregation requires 'percentile' parameter")
            
            percentile = parameters["percentile"]
            if not isinstance(percentile, (int, float)) or percentile < 0 or percentile > 100:
                raise ValidationError("Percentile must be a number between 0 and 100")
        
        # Validate grouping parameters
        if "group_by" in parameters:
            valid_group_by = {"hour", "day", "week", "month", "service", "user", "status"}
            group_by = parameters["group_by"]
            
            if isinstance(group_by, str):
                group_by = [group_by]
            
            if not isinstance(group_by, list):
                raise ValidationError("group_by must be a string or list of strings")
            
            invalid_groups = set(group_by) - valid_group_by
            if invalid_groups:
                raise ValidationError(
                    f"Invalid group_by values: {invalid_groups}. "
                    f"Valid options: {', '.join(valid_group_by)}"
                )
        
        logger.debug(
            "analytics.validation.aggregation_validated",
            aggregation_type=aggregation_type,
            parameters=parameters
        )
    
    def _validate_date_range(self, start_date: str, end_date: str) -> None:
        """Validate date range parameters."""
        from datetime import datetime
        
        try:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError as e:
            raise ValidationError(f"Invalid date format: {e}")
        
        if start >= end:
            raise ValidationError("start_date must be before end_date")
        
        # Limit date range to prevent excessive queries
        max_days = 365  # 1 year
        if (end - start).days > max_days:
            raise ValidationError(f"Date range cannot exceed {max_days} days")