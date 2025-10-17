"""
Command Pattern implementation for operation queuing and undo/redo functionality
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid
import asyncio
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CommandStatus(str, Enum):
    """Command execution status"""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNDONE = "undone"


@dataclass
class CommandResult:
    """Result of command execution"""
    command_id: str
    status: CommandStatus
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class ICommand(ABC):
    """Base interface for all commands"""
    
    def __init__(self, command_id: Optional[str] = None):
        self.command_id = command_id or str(uuid.uuid4())
        self.timestamp = datetime.now()
        self.metadata: Dict[str, Any] = {}
    
    @abstractmethod
    async def execute(self) -> Any:
        """Execute the command"""
        pass
    
    async def undo(self) -> Any:
        """Undo the command (optional)"""
        raise NotImplementedError("Command does not support undo operation")
    
    def can_undo(self) -> bool:
        """Check if command supports undo"""
        try:
            # Check if undo method is implemented
            return self.__class__.undo != ICommand.undo
        except:
            return False
    
    def get_description(self) -> str:
        """Get human-readable description of the command"""
        return f"{self.__class__.__name__}({self.command_id})"


class ICommandHandler(ABC):
    """Base interface for command handlers"""
    
    @abstractmethod
    async def handle(self, command: ICommand) -> CommandResult:
        """Handle command execution"""
        pass
    
    @abstractmethod
    def can_handle(self, command: ICommand) -> bool:
        """Check if handler can handle this command type"""
        pass


class BaseCommandHandler(ICommandHandler):
    """Base implementation of command handler"""
    
    def __init__(self, command_type: Type[ICommand]):
        self.command_type = command_type
    
    async def handle(self, command: ICommand) -> CommandResult:
        """Handle command with error handling and timing"""
        
        if not self.can_handle(command):
            return CommandResult(
                command_id=command.command_id,
                status=CommandStatus.FAILED,
                error=f"Handler cannot handle command type {type(command).__name__}"
            )
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"Executing command: {command.get_description()}")
            
            result = await command.execute()
            
            end_time = asyncio.get_event_loop().time()
            execution_time = end_time - start_time
            
            logger.info(
                f"Command completed: {command.get_description()} in {execution_time:.3f}s"
            )
            
            return CommandResult(
                command_id=command.command_id,
                status=CommandStatus.COMPLETED,
                result=result,
                execution_time=execution_time,
                metadata=command.metadata
            )
            
        except Exception as e:
            end_time = asyncio.get_event_loop().time()
            execution_time = end_time - start_time
            
            logger.error(
                f"Command failed: {command.get_description()} - {str(e)}",
                exc_info=True
            )
            
            return CommandResult(
                command_id=command.command_id,
                status=CommandStatus.FAILED,
                error=str(e),
                execution_time=execution_time,
                metadata=command.metadata
            )
    
    def can_handle(self, command: ICommand) -> bool:
        """Check if this handler can handle the command"""
        return isinstance(command, self.command_type)


class CommandInvoker:
    """Invoker for executing commands with history and undo support"""
    
    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.handlers: Dict[Type[ICommand], ICommandHandler] = {}
        self.command_history: List[CommandResult] = []
        self.undo_stack: List[ICommand] = []
        self.redo_stack: List[ICommand] = []
    
    def register_handler(self, command_type: Type[ICommand], handler: ICommandHandler):
        """Register a command handler"""
        self.handlers[command_type] = handler
        logger.info(f"Registered handler for {command_type.__name__}")
    
    async def execute_command(self, command: ICommand) -> CommandResult:
        """Execute a command"""
        
        # Find appropriate handler
        handler = self._find_handler(command)
        if not handler:
            error_msg = f"No handler found for command type {type(command).__name__}"
            logger.error(error_msg)
            return CommandResult(
                command_id=command.command_id,
                status=CommandStatus.FAILED,
                error=error_msg
            )
        
        # Execute command
        result = await handler.handle(command)
        
        # Add to history
        self._add_to_history(result)
        
        # Add to undo stack if command supports undo and execution was successful
        if command.can_undo() and result.status == CommandStatus.COMPLETED:
            self.undo_stack.append(command)
            # Clear redo stack when new command is executed
            self.redo_stack.clear()
        
        return result
    
    async def undo_last_command(self) -> Optional[CommandResult]:
        """Undo the last command"""
        
        if not self.undo_stack:
            logger.warning("No commands to undo")
            return None
        
        command = self.undo_stack.pop()
        
        try:
            logger.info(f"Undoing command: {command.get_description()}")
            
            start_time = asyncio.get_event_loop().time()
            result = await command.undo()
            end_time = asyncio.get_event_loop().time()
            
            # Add to redo stack
            self.redo_stack.append(command)
            
            undo_result = CommandResult(
                command_id=f"undo_{command.command_id}",
                status=CommandStatus.UNDONE,
                result=result,
                execution_time=end_time - start_time,
                metadata={"original_command": command.command_id}
            )
            
            self._add_to_history(undo_result)
            
            logger.info(f"Command undone: {command.get_description()}")
            return undo_result
            
        except Exception as e:
            logger.error(f"Failed to undo command: {command.get_description()} - {str(e)}")
            # Put command back on undo stack
            self.undo_stack.append(command)
            
            return CommandResult(
                command_id=f"undo_{command.command_id}",
                status=CommandStatus.FAILED,
                error=f"Undo failed: {str(e)}",
                metadata={"original_command": command.command_id}
            )
    
    async def redo_last_command(self) -> Optional[CommandResult]:
        """Redo the last undone command"""
        
        if not self.redo_stack:
            logger.warning("No commands to redo")
            return None
        
        command = self.redo_stack.pop()
        
        # Re-execute the command
        result = await self.execute_command(command)
        
        logger.info(f"Command redone: {command.get_description()}")
        return result
    
    def get_command_history(self, limit: Optional[int] = None) -> List[CommandResult]:
        """Get command execution history"""
        if limit:
            return self.command_history[-limit:]
        return self.command_history.copy()
    
    def get_undo_stack_info(self) -> List[str]:
        """Get information about commands that can be undone"""
        return [cmd.get_description() for cmd in self.undo_stack]
    
    def get_redo_stack_info(self) -> List[str]:
        """Get information about commands that can be redone"""
        return [cmd.get_description() for cmd in self.redo_stack]
    
    def clear_history(self):
        """Clear command history and stacks"""
        self.command_history.clear()
        self.undo_stack.clear()
        self.redo_stack.clear()
        logger.info("Command history cleared")
    
    def _find_handler(self, command: ICommand) -> Optional[ICommandHandler]:
        """Find appropriate handler for command"""
        
        # Try exact type match first
        command_type = type(command)
        if command_type in self.handlers:
            return self.handlers[command_type]
        
        # Try base class matches
        for registered_type, handler in self.handlers.items():
            if isinstance(command, registered_type):
                return handler
        
        return None
    
    def _add_to_history(self, result: CommandResult):
        """Add command result to history"""
        self.command_history.append(result)
        
        # Maintain history size limit
        if len(self.command_history) > self.max_history:
            self.command_history.pop(0)


class MacroCommand(ICommand):
    """Command that executes multiple commands in sequence"""
    
    def __init__(self, commands: List[ICommand], command_id: Optional[str] = None):
        super().__init__(command_id)
        self.commands = commands
        self.executed_commands: List[ICommand] = []
    
    async def execute(self) -> List[Any]:
        """Execute all commands in sequence"""
        results = []
        
        for command in self.commands:
            try:
                result = await command.execute()
                results.append(result)
                self.executed_commands.append(command)
            except Exception as e:
                logger.error(f"Macro command failed at {command.get_description()}: {e}")
                # Attempt to undo executed commands
                await self.undo()
                raise
        
        return results
    
    async def undo(self) -> List[Any]:
        """Undo all executed commands in reverse order"""
        undo_results = []
        
        # Undo in reverse order
        for command in reversed(self.executed_commands):
            if command.can_undo():
                try:
                    result = await command.undo()
                    undo_results.append(result)
                except Exception as e:
                    logger.error(f"Failed to undo command in macro: {command.get_description()} - {e}")
        
        self.executed_commands.clear()
        return undo_results
    
    def can_undo(self) -> bool:
        """Macro can undo if any of its commands can undo"""
        return any(cmd.can_undo() for cmd in self.executed_commands)
    
    def get_description(self) -> str:
        """Get description of macro command"""
        return f"MacroCommand({len(self.commands)} commands, {self.command_id})"


class CommandQueue:
    """Queue for managing command execution with priority and scheduling"""
    
    def __init__(self, invoker: CommandInvoker, max_concurrent: int = 5):
        self.invoker = invoker
        self.max_concurrent = max_concurrent
        self.queue: List[tuple[ICommand, int]] = []  # (command, priority)
        self.executing: Dict[str, asyncio.Task] = {}
        self.results: Dict[str, CommandResult] = {}
        self.is_processing = False
    
    async def enqueue_command(self, command: ICommand, priority: int = 0) -> str:
        """Add command to queue with priority"""
        self.queue.append((command, priority))
        
        # Sort by priority (higher priority first)
        self.queue.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"Command queued: {command.get_description()} (priority: {priority})")
        
        # Start processing if not already running
        if not self.is_processing:
            asyncio.create_task(self._process_queue())
        
        return command.command_id
    
    async def _process_queue(self):
        """Process commands in the queue"""
        self.is_processing = True
        
        try:
            while self.queue or self.executing:
                # Start new commands up to max concurrent limit
                while (len(self.executing) < self.max_concurrent and self.queue):
                    command, _ = self.queue.pop(0)
                    
                    task = asyncio.create_task(self._execute_command_async(command))
                    self.executing[command.command_id] = task
                    
                    logger.info(f"Started executing: {command.get_description()}")
                
                # Wait for at least one command to complete
                if self.executing:
                    done, pending = await asyncio.wait(
                        self.executing.values(),
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    # Process completed commands
                    for task in done:
                        command_id = next(
                            cmd_id for cmd_id, t in self.executing.items() if t == task
                        )
                        del self.executing[command_id]
                        
                        try:
                            result = await task
                            self.results[command_id] = result
                            logger.info(f"Command completed: {command_id}")
                        except Exception as e:
                            logger.error(f"Command failed: {command_id} - {e}")
        
        finally:
            self.is_processing = False
    
    async def _execute_command_async(self, command: ICommand) -> CommandResult:
        """Execute command asynchronously"""
        return await self.invoker.execute_command(command)
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        return {
            "queued_commands": len(self.queue),
            "executing_commands": len(self.executing),
            "completed_commands": len(self.results),
            "max_concurrent": self.max_concurrent,
            "is_processing": self.is_processing
        }
    
    def get_command_result(self, command_id: str) -> Optional[CommandResult]:
        """Get result of executed command"""
        return self.results.get(command_id)


# Command registry for managing command types
class CommandRegistry:
    """Registry for managing command types and their handlers"""
    
    _commands: Dict[str, Type[ICommand]] = {}
    _handlers: Dict[Type[ICommand], Type[ICommandHandler]] = {}
    
    @classmethod
    def register_command(
        cls, 
        name: str, 
        command_class: Type[ICommand],
        handler_class: Type[ICommandHandler] = None
    ):
        """Register a command type"""
        cls._commands[name] = command_class
        if handler_class:
            cls._handlers[command_class] = handler_class
        
        logger.info(f"Registered command: {name}")
    
    @classmethod
    def get_command_class(cls, name: str) -> Optional[Type[ICommand]]:
        """Get command class by name"""
        return cls._commands.get(name)
    
    @classmethod
    def get_handler_class(cls, command_class: Type[ICommand]) -> Optional[Type[ICommandHandler]]:
        """Get handler class for command"""
        return cls._handlers.get(command_class)
    
    @classmethod
    def create_invoker(cls) -> CommandInvoker:
        """Create command invoker with registered handlers"""
        invoker = CommandInvoker()
        
        for command_class, handler_class in cls._handlers.items():
            handler = handler_class()
            invoker.register_handler(command_class, handler)
        
        return invoker
    
    @classmethod
    def get_available_commands(cls) -> List[str]:
        """Get list of available command names"""
        return list(cls._commands.keys())