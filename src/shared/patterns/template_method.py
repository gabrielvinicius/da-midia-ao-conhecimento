"""
Template Method Pattern implementation for algorithmic frameworks
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, TypeVar, Generic
from dataclasses import dataclass
from enum import Enum
import time
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')  # Input type
R = TypeVar('R')  # Result type


class ProcessingStage(str, Enum):
    """Standard processing stages for template methods"""
    INITIALIZE = "initialize"
    VALIDATE = "validate"
    PREPROCESS = "preprocess"
    PROCESS = "process"
    POSTPROCESS = "postprocess"
    FINALIZE = "finalize"


@dataclass
class ProcessingResult:
    """Result container for template method processing"""
    success: bool
    result: Any = None
    metadata: Dict[str, Any] = None
    errors: List[str] = None
    stage_results: Dict[ProcessingStage, Any] = None
    processing_time: float = 0
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.errors is None:
            self.errors = []
        if self.stage_results is None:
            self.stage_results = {}
    
    def add_error(self, error: str) -> None:
        """Add error to result"""
        self.errors.append(error)
        self.success = False
    
    def add_stage_result(self, stage: ProcessingStage, result: Any) -> None:
        """Add stage-specific result"""
        self.stage_results[stage] = result
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata"""
        self.metadata[key] = value


class TemplateMethodBase(ABC, Generic[T, R]):
    """
    Base class for Template Method Pattern implementation.
    Defines the skeleton of an algorithm in the base class,
    letting subclasses override specific steps without changing the algorithm structure.
    """
    
    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
        self.processing_result = ProcessingResult(success=True)
    
    async def execute(self, input_data: T, options: Dict[str, Any] = None) -> ProcessingResult:
        """
        Template method that defines the algorithm skeleton.
        This is the main entry point that orchestrates the entire process.
        """
        start_time = time.time()
        self.processing_result = ProcessingResult(success=True)
        options = options or {}
        
        logger.info(
            f"Starting template method execution: {self.name}",
            extra={
                "template": self.name,
                "input_type": type(input_data).__name__,
                "options": options
            }
        )
        
        try:
            # Step 1: Initialize (required)
            if not await self._execute_stage(ProcessingStage.INITIALIZE, input_data, options):
                return self.processing_result
            
            # Step 2: Validate (required)
            if not await self._execute_stage(ProcessingStage.VALIDATE, input_data, options):
                return self.processing_result
            
            # Step 3: Preprocess (optional hook)
            if self._should_preprocess():
                if not await self._execute_stage(ProcessingStage.PREPROCESS, input_data, options):
                    return self.processing_result
            
            # Step 4: Process (required - core algorithm)
            if not await self._execute_stage(ProcessingStage.PROCESS, input_data, options):
                return self.processing_result
            
            # Step 5: Postprocess (optional hook)
            if self._should_postprocess():
                if not await self._execute_stage(ProcessingStage.POSTPROCESS, input_data, options):
                    return self.processing_result
            
            # Step 6: Finalize (required)
            if not await self._execute_stage(ProcessingStage.FINALIZE, input_data, options):
                return self.processing_result
            
            # Success
            end_time = time.time()
            self.processing_result.processing_time = end_time - start_time
            
            logger.info(
                f"Template method execution completed: {self.name}",
                extra={
                    "template": self.name,
                    "success": True,
                    "processing_time": self.processing_result.processing_time
                }
            )
            
            return self.processing_result
            
        except Exception as e:
            end_time = time.time()
            self.processing_result.processing_time = end_time - start_time
            self.processing_result.add_error(f"Template execution failed: {str(e)}")
            
            logger.error(
                f"Template method execution failed: {self.name}",
                extra={
                    "template": self.name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "processing_time": self.processing_result.processing_time
                },
                exc_info=True
            )
            
            return self.processing_result
    
    async def _execute_stage(
        self, 
        stage: ProcessingStage, 
        input_data: T, 
        options: Dict[str, Any]
    ) -> bool:
        """Execute a specific processing stage"""
        
        try:
            stage_start = time.time()
            
            # Call the appropriate stage method
            stage_method = getattr(self, f"_{stage.value}")
            result = await stage_method(input_data, options)
            
            stage_end = time.time()
            stage_duration = stage_end - stage_start
            
            # Store stage result
            self.processing_result.add_stage_result(stage, result)
            self.processing_result.add_metadata(f"{stage.value}_duration", stage_duration)
            
            logger.debug(
                f"Stage {stage.value} completed",
                extra={
                    "template": self.name,
                    "stage": stage.value,
                    "duration": stage_duration,
                    "result_type": type(result).__name__ if result else None
                }
            )
            
            return True
            
        except Exception as e:
            self.processing_result.add_error(f"Stage {stage.value} failed: {str(e)}")
            
            logger.error(
                f"Stage {stage.value} failed",
                extra={
                    "template": self.name,
                    "stage": stage.value,
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                exc_info=True
            )
            
            return False
    
    # Template method steps - subclasses must implement these
    
    @abstractmethod
    async def _initialize(self, input_data: T, options: Dict[str, Any]) -> Any:
        """Initialize the algorithm. Required step."""
        pass
    
    @abstractmethod
    async def _validate(self, input_data: T, options: Dict[str, Any]) -> bool:
        """Validate input data. Required step. Return True if valid."""
        pass
    
    @abstractmethod
    async def _process(self, input_data: T, options: Dict[str, Any]) -> R:
        """Core processing logic. Required step."""
        pass
    
    @abstractmethod
    async def _finalize(self, input_data: T, options: Dict[str, Any]) -> R:
        """Finalize and return result. Required step."""
        pass
    
    # Optional hooks - subclasses can override these
    
    async def _preprocess(self, input_data: T, options: Dict[str, Any]) -> Any:
        """Optional preprocessing step. Override if needed."""
        return None
    
    async def _postprocess(self, input_data: T, options: Dict[str, Any]) -> Any:
        """Optional postprocessing step. Override if needed."""
        return None
    
    # Hook methods - subclasses can override to control execution flow
    
    def _should_preprocess(self) -> bool:
        """Determine if preprocessing should be executed. Hook method."""
        return False
    
    def _should_postprocess(self) -> bool:
        """Determine if postprocessing should be executed. Hook method."""
        return False
    
    def _get_algorithm_name(self) -> str:
        """Get algorithm name for logging. Hook method."""
        return self.name
    
    def _get_supported_options(self) -> List[str]:
        """Get list of supported options. Hook method."""
        return []


class EnhancedTemplateMethod(TemplateMethodBase[T, R]):
    """
    Enhanced template method with additional features:
    - Progress tracking
    - Cancellation support
    - Resource management
    - Performance monitoring
    """
    
    def __init__(self, name: str = None):
        super().__init__(name)
        self._cancelled = False
        self._progress = 0.0
        self._total_stages = 6
        self._current_stage = 0
    
    def cancel(self) -> None:
        """Cancel the execution"""
        self._cancelled = True
    
    def get_progress(self) -> float:
        """Get execution progress (0.0 to 1.0)"""
        return self._progress
    
    async def _execute_stage(
        self, 
        stage: ProcessingStage, 
        input_data: T, 
        options: Dict[str, Any]
    ) -> bool:
        """Enhanced stage execution with progress tracking and cancellation"""
        
        # Check for cancellation
        if self._cancelled:
            self.processing_result.add_error("Execution was cancelled")
            return False
        
        # Update progress
        self._current_stage += 1
        self._progress = self._current_stage / self._total_stages
        
        # Call pre-stage hook
        await self._before_stage(stage, input_data, options)
        
        # Execute stage
        success = await super()._execute_stage(stage, input_data, options)
        
        # Call post-stage hook
        await self._after_stage(stage, input_data, options, success)
        
        return success
    
    async def _before_stage(
        self, 
        stage: ProcessingStage, 
        input_data: T, 
        options: Dict[str, Any]
    ) -> None:
        """Hook called before each stage. Override for custom behavior."""
        pass
    
    async def _after_stage(
        self, 
        stage: ProcessingStage, 
        input_data: T, 
        options: Dict[str, Any],
        success: bool
    ) -> None:
        """Hook called after each stage. Override for custom behavior."""
        pass


class TemplateMethodFactory:
    """Factory for creating and managing template method instances"""
    
    _templates: Dict[str, type] = {}
    
    @classmethod
    def register_template(cls, name: str, template_class: type):
        """Register a template method class"""
        cls._templates[name] = template_class
        logger.info(f"Registered template method: {name}")
    
    @classmethod
    def create_template(cls, name: str, **kwargs) -> TemplateMethodBase:
        """Create template method instance"""
        template_class = cls._templates.get(name)
        if not template_class:
            raise ValueError(f"Template method '{name}' not found")
        
        return template_class(**kwargs)
    
    @classmethod
    def get_available_templates(cls) -> List[str]:
        """Get list of available template methods"""
        return list(cls._templates.keys())
    
    @classmethod
    def get_template_info(cls, name: str) -> Dict[str, Any]:
        """Get information about a template method"""
        template_class = cls._templates.get(name)
        if not template_class:
            return {}
        
        return {
            "name": name,
            "class": template_class.__name__,
            "module": template_class.__module__,
            "doc": template_class.__doc__ or "No documentation available"
        }


class ConditionalTemplateMethod(TemplateMethodBase[T, R]):
    """
    Template method with conditional step execution based on runtime conditions
    """
    
    def __init__(self, name: str = None):
        super().__init__(name)
        self._conditions: Dict[ProcessingStage, callable] = {}
    
    def add_condition(self, stage: ProcessingStage, condition: callable):
        """Add condition for stage execution"""
        self._conditions[stage] = condition
    
    async def _execute_stage(
        self, 
        stage: ProcessingStage, 
        input_data: T, 
        options: Dict[str, Any]
    ) -> bool:
        """Execute stage only if condition is met"""
        
        # Check condition for this stage
        condition = self._conditions.get(stage)
        if condition and not condition(input_data, options, self.processing_result):
            logger.debug(
                f"Skipping stage {stage.value} due to condition",
                extra={"template": self.name, "stage": stage.value}
            )
            return True
        
        return await super()._execute_stage(stage, input_data, options)


class ParallelTemplateMethod(TemplateMethodBase[T, R]):
    """
    Template method that can execute certain stages in parallel
    """
    
    def __init__(self, name: str = None):
        super().__init__(name)
        self._parallel_stages: List[ProcessingStage] = []
    
    def add_parallel_stage(self, stage: ProcessingStage):
        """Mark a stage for parallel execution"""
        self._parallel_stages.append(stage)
    
    async def _execute_parallel_stages(
        self, 
        stages: List[ProcessingStage],
        input_data: T, 
        options: Dict[str, Any]
    ) -> bool:
        """Execute multiple stages in parallel"""
        import asyncio
        
        tasks = []
        for stage in stages:
            task = asyncio.create_task(
                self._execute_stage(stage, input_data, options)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check if all stages succeeded
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.processing_result.add_error(
                    f"Parallel stage {stages[i].value} failed: {str(result)}"
                )
                return False
            elif not result:
                return False
        
        return True