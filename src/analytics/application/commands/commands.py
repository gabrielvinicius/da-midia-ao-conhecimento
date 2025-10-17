"""
Analytics Commands - Pure data classes following Command Pattern
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass(frozen=True)
class GenerateReportCommand:
    """Command to generate analytics report"""
    report_type: str
    start_date: datetime
    end_date: datetime
    filters: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class TrackEventCommand:
    """Command to track analytics event"""
    event_name: str
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None