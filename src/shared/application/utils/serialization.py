from __future__ import annotations

import uuid
from collections.abc import Mapping
from enum import Enum
from typing import Any


def to_json_serializable(obj: Any) -> Any:
    """
    Recursively convert objects to JSON-serializable types.
    Handles:
    - dict/Mapping -> dict
    - list/tuple/set/sequence -> list
    - Enum -> value
    - UUID -> str
    - numpy ndarray -> list (if numpy is installed)
    - numpy scalars -> int/float (if numpy is installed)
    - objects with __dict__ -> dict
    """
    if obj is None:
        return None

    # Handle Mapping (including mappingproxy and dict)
    if isinstance(obj, Mapping):
        return {str(k): to_json_serializable(v) for k, v in obj.items()}

    # Handle Sequences (list, tuple, set)
    if isinstance(obj, (list, tuple, set)):
        return [to_json_serializable(v) for v in obj]

    # Handle Enum
    if isinstance(obj, Enum):
        return obj.value

    # Handle UUID
    if isinstance(obj, uuid.UUID):
        return str(obj)

    # Handle Numpy types if available
    try:
        import numpy as np
        if isinstance(obj, np.ndarray):
            return to_json_serializable(obj.tolist())
        if isinstance(obj, (np.integer, np.floating)):
            return obj.item()
    except (ImportError, AttributeError):
        pass

    # Handle objects with __dict__ (excluding types/classes)
    if hasattr(obj, "__dict__") and not isinstance(obj, type):
        return to_json_serializable(obj.__dict__)

    # Fallback for complex objects that might have tolist (like some pandas types)
    if hasattr(obj, "tolist") and callable(getattr(obj, "tolist")):
        return to_json_serializable(obj.tolist())

    return obj
