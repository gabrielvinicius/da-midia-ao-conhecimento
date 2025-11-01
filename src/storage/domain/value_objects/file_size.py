# src/storage/domain/value_objects/file_size.py
from dataclasses import dataclass


@dataclass(frozen=True)
class FileSize:
    """Value object representing file size with validation."""
    
    bytes: int
    
    def __post_init__(self):
        if self.bytes < 0:
            raise ValueError("File size cannot be negative")
    
    @property
    def kb(self) -> float:
        """Size in kilobytes."""
        return self.bytes / 1024
    
    @property
    def mb(self) -> float:
        """Size in megabytes."""
        return self.bytes / (1024 * 1024)
    
    @property
    def gb(self) -> float:
        """Size in gigabytes."""
        return self.bytes / (1024 * 1024 * 1024)
    
    def __str__(self) -> str:
        if self.bytes < 1024:
            return f"{self.bytes} B"
        elif self.bytes < 1024 * 1024:
            return f"{self.kb:.2f} KB"
        elif self.bytes < 1024 * 1024 * 1024:
            return f"{self.mb:.2f} MB"
        else:
            return f"{self.gb:.2f} GB"
