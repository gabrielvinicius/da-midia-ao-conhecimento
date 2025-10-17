"""
Integration of Command Pattern with existing patterns
"""
from typing import Any, Dict, List, Optional, Callable
from functools import wraps

from src.shared.decorators.base_decorator import BaseAsyncDecorator
from src.shared.patterns.command import (
    ICommand, CommandInvoker, CommandResult, CommandRegistry,
    CommandQueue, MacroCommand
)


class CommandDecorator(BaseAsyncDecorator):
    """Decorator that wraps service methods in commands"""
    
    def __init__(
        self,
        command_class: type = None,
        invoker: CommandInvoker = None,
        auto_execute: bool = True,
        store_in_history: bool = True
    ):
        super().__init__("command")
        self.command_class = command_class
        self.invoker = invoker or CommandRegistry.create_invoker()
        self.auto_execute = auto_execute
        self.store_in_history = store_in_history
        self.command_result: Optional[CommandResult] = None
    
    async def _before_execution(self, *args, **kwargs) -> Optional[Any]:
        """Create and optionally execute command before method execution"""
        
        if self.command_class:
            # Build command from method arguments
            command = self._build_command(*args, **kwargs)
            
            if self.auto_execute:
                # Execute command and return result
                self.command_result = await self.invoker.execute_command(command)
                return self.command_result.result
            else:
                # Store command for later execution
                self._pending_command = command
                return None
        
        return None
    
    async def _after_execution(self, result: Any, *args, **kwargs) -> Any:
        """Process command results after method execution"""
        
        if self.command_result:
            # Combine original result with command result
            return {
                "method_result": result,
                "command_result": self.command_result.result,
                "command_status": self.command_result.status.value,
                "command_id": self.command_result.command_id
            }
        
        return result
    
    async def _on_exception(self, exception: Exception, *args, **kwargs) -> None:
        """Handle command exceptions"""
        if hasattr(self, '_pending_command'):
            # Command was created but not executed
            pass
    
    def _build_command(self, *args, **kwargs) -> ICommand:
        """Build command from method arguments - override in subclasses"""
        if self.command_class:
            return self.command_class(*args, **kwargs)
        raise NotImplementedError("Command class not specified")


class AsyncCommand(ICommand):
    """Base class for asynchronous commands"""
    
    def __init__(self, method: Callable, args: tuple, kwargs: dict, command_id: str = None):
        super().__init__(command_id)
        self.method = method
        self.args = args
        self.kwargs = kwargs
        self.result = None
    
    async def execute(self) -> Any:
        """Execute the async method"""
        self.result = await self.method(*self.args, **self.kwargs)
        return self.result
    
    def get_description(self) -> str:
        """Get description of the command"""
        return f"{self.method.__name__}({self.command_id})"


# Convenience decorators for common command patterns
def async_command(command_class: type = None, invoker: CommandInvoker = None):
    """Decorator to wrap async methods in commands"""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create command
            if command_class:
                command = command_class(*args, **kwargs)
            else:
                command = AsyncCommand(func, args, kwargs)
            
            # Execute command
            command_invoker = invoker or CommandRegistry.create_invoker()
            result = await command_invoker.execute_command(command)
            
            if result.status.value == "completed":
                return result.result
            else:
                raise Exception(f"Command failed: {result.error}")
        
        return wrapper
    return decorator


def undoable_command(command_class: type):
    """Decorator for commands that support undo operations"""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute original function
            result = await func(*args, **kwargs)
            
            # Store command for potential undo
            command = command_class(*args, **kwargs)
            # Add to global undo stack or context-specific stack
            
            return result
        
        return wrapper
    return decorator


class CommandFactory:
    """Factory for creating different types of commands"""
    
    @staticmethod
    def create_media_upload_command(user_id: str, file_data: bytes, filename: str):
        """Create media upload command"""
        from src.media_management.application.commands.interfaces import ICreateMediaCommand
        
        class MediaUploadCommand(ICommand):
            def __init__(self):
                super().__init__()
                self.user_id = user_id
                self.file_data = file_data
                self.filename = filename
            
            async def execute(self):
                # Implementation would call actual media service
                return {"status": "uploaded", "filename": self.filename}
            
            def get_description(self):
                return f"Upload {self.filename} for user {self.user_id}"
        
        return MediaUploadCommand()
    
    @staticmethod
    def create_batch_command(commands: List[ICommand]):
        """Create macro command for batch operations"""
        return MacroCommand(commands)


# Integration with existing patterns
class CommandChainIntegration:
    """Integration between Command Pattern and Chain of Responsibility"""
    
    @staticmethod
    def create_command_pipeline_stage(command_class: type, invoker: CommandInvoker = None):
        """Create pipeline stage that executes commands"""
        
        from src.shared.patterns.chain_of_responsibility import BaseChainHandler, HandlerResult
        
        class CommandPipelineHandler(BaseChainHandler):
            def __init__(self):
                super().__init__("CommandHandler")
                self.command_invoker = invoker or CommandRegistry.create_invoker()
            
            async def process(self, context) -> HandlerResult:
                """Execute command from context"""
                
                if hasattr(context.request, 'command_data'):
                    command = command_class(**context.request.command_data)
                    result = await self.command_invoker.execute_command(command)
                    
                    context.add_metadata("command_result", result)
                    
                    if result.status.value == "completed":
                        return HandlerResult.CONTINUE
                    else:
                        context.add_error(f"Command failed: {result.error}")
                        return HandlerResult.ABORT
                
                return HandlerResult.CONTINUE
        
        return CommandPipelineHandler()


class CommandTemplateIntegration:
    """Integration between Command Pattern and Template Method"""
    
    @staticmethod
    def create_command_template_stage(command_classes: List[type]):
        """Create template stage that executes commands"""
        
        from src.shared.patterns.template_method import BaseAsyncDecorator
        
        class CommandTemplateStage(BaseAsyncDecorator):
            def __init__(self):
                super().__init__("command_template")
                self.command_invoker = CommandRegistry.create_invoker()
            
            async def _after_execution(self, result: Any, *args, **kwargs) -> Any:
                """Execute commands after template execution"""
                
                command_results = []
                for command_class in command_classes:
                    try:
                        command = command_class(*args, **kwargs)
                        cmd_result = await self.command_invoker.execute_command(command)
                        command_results.append(cmd_result)
                    except Exception as e:
                        command_results.append({"error": str(e)})
                
                if hasattr(result, 'command_results'):
                    result.command_results = command_results
                
                return result
        
        return CommandTemplateStage()


# Example command implementations
class ExampleCreateUserCommand(ICommand):
    """Example command for user creation"""
    
    def __init__(self, username: str, email: str, password: str):
        super().__init__()
        self.username = username
        self.email = email
        self.password = password
        self.created_user_id = None
    
    async def execute(self) -> Dict[str, Any]:
        """Execute user creation"""
        # Simulate user creation
        import uuid
        self.created_user_id = str(uuid.uuid4())
        
        return {
            "user_id": self.created_user_id,
            "username": self.username,
            "email": self.email,
            "created": True
        }
    
    async def undo(self) -> Dict[str, Any]:
        """Undo user creation"""
        if self.created_user_id:
            # Simulate user deletion
            return {
                "user_id": self.created_user_id,
                "deleted": True
            }
        return {"error": "No user to undo"}
    
    def get_description(self) -> str:
        return f"CreateUser({self.username}, {self.email})"


# Command monitoring and analytics
class CommandAnalytics:
    """Analytics for command execution patterns"""
    
    def __init__(self, invoker: CommandInvoker):
        self.invoker = invoker
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get command execution statistics"""
        history = self.invoker.get_command_history()
        
        if not history:
            return {"total_commands": 0}
        
        total_commands = len(history)
        successful = sum(1 for h in history if h.status.value == "completed")
        failed = sum(1 for h in history if h.status.value == "failed")
        
        avg_execution_time = sum(h.execution_time for h in history) / total_commands
        
        return {
            "total_commands": total_commands,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total_commands) * 100,
            "avg_execution_time": avg_execution_time,
            "can_undo": len(self.invoker.get_undo_stack_info()),
            "can_redo": len(self.invoker.get_redo_stack_info())
        }
    
    def get_command_types_stats(self) -> Dict[str, int]:
        """Get statistics by command type"""
        history = self.invoker.get_command_history()
        
        type_counts = {}
        for result in history:
            # Extract command type from command_id or metadata
            cmd_type = result.metadata.get('command_type', 'unknown')
            type_counts[cmd_type] = type_counts.get(cmd_type, 0) + 1
        
        return type_counts


# Registration helper
def register_common_commands():
    """Register commonly used commands"""
    
    CommandRegistry.register_command(
        "create_user",
        ExampleCreateUserCommand
    )
    
    print("✅ Common commands registered")


# Usage example
async def demonstrate_command_pattern():
    """Demonstrate command pattern usage"""
    
    # Register commands
    register_common_commands()
    
    # Create invoker
    invoker = CommandRegistry.create_invoker()
    
    # Execute commands
    cmd1 = ExampleCreateUserCommand("john_doe", "john@example.com", "password123")
    result1 = await invoker.execute_command(cmd1)
    
    print(f"Command result: {result1}")
    
    # Undo command
    undo_result = await invoker.undo_last_command()
    print(f"Undo result: {undo_result}")
    
    # Get analytics
    analytics = CommandAnalytics(invoker)
    stats = analytics.get_execution_stats()
    print(f"Execution stats: {stats}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(demonstrate_command_pattern())