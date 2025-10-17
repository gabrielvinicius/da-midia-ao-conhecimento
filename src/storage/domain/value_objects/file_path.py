# src/storage/domain/value_objects/file_path.py
from dataclasses import dataclass
from pathlib import Path
from typing import Union


@dataclass(frozen=True)
class FilePath:
    """Value object representing a file path with validation."""
    
    value: str
    
    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("File path cannot be empty")
        
        # Normalize path separators
        object.__setattr__(self, 'value', str(Path(self.value).as_posix()))
    
    @classmethod
    def from_path(cls, path: Union[str, Path]) -> 'FilePath':
        """Create FilePath from string or Path object."""
        return cls(str(path))
    
    def to_path(self) -> Path:
        """Convert to pathlib.Path."""
        return Path(self.value)
    
    def get_extension(self) -> str:
        """Get file extension."""
        return Path(self.value).suffix.lower()
    
    def get_filename(self) -> str:
        """Get filename without path."""
        return Path(self.value).name
    
    def __str__(self) -> str:
        return self.value