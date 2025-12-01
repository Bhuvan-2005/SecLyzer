"""
Input validation schemas for SecLyzer events
Uses Pydantic for robust type checking and validation
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import datetime


class KeystrokeEvent(BaseModel):
    """Schema for keyboard events"""
    type: Literal['keystroke'] = 'keystroke'
    event: Literal['press', 'release']
    key: str = Field(..., min_length=1, max_length=100)
    ts: int = Field(..., gt=0)  # Microseconds since epoch
    scan_code: Optional[int] = Field(None, ge=0, le=65535)
    
    @field_validator('ts')
    @classmethod
    def validate_timestamp(cls, v):
        # Ensure timestamp is reasonable (not too far in past/future)
        current_time_us = int(datetime.now().timestamp() * 1_000_000)
        # Allow 1 hour in past or future
        if abs(v - current_time_us) > 3_600_000_000:
            raise ValueError('Timestamp too far from current time')
        return v


class MouseEvent(BaseModel):
    """Schema for mouse events"""
    type: Literal['mouse'] = 'mouse'
    event: Literal['move', 'press', 'release', 'scroll']
    ts: int = Field(..., gt=0)
    x: Optional[int] = Field(None, ge=0, le=10000)  # Max reasonable screen size
    y: Optional[int] = Field(None, ge=0, le=10000)
    button: Optional[str] = Field(None, pattern='^(Left|Right|Middle)$')
    scroll_delta: Optional[int] = Field(None, ge=-1000, le=1000)
    
    @field_validator('ts')
    @classmethod
    def validate_timestamp(cls, v):
        current_time_us = int(datetime.now().timestamp() * 1_000_000)
        if abs(v - current_time_us) > 3_600_000_000:
            raise ValueError('Timestamp too far from current time')
        return v


class AppEvent(BaseModel):
    """Schema for application switch events"""
    type: Literal['app'] = 'app'
    app_name: str = Field(..., min_length=1, max_length=500)
    ts: int = Field(..., gt=0)
    
    @field_validator('app_name')
    @classmethod
    def sanitize_app_name(cls, v):
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '&', '"', "'", '\\', '/', '\0']
        for char in dangerous_chars:
            v = v.replace(char, '')
        return v.strip()
    
    @field_validator('ts')
    @classmethod
    def validate_timestamp(cls, v):
        current_time_us = int(datetime.now().timestamp() * 1_000_000)
        if abs(v - current_time_us) > 3_600_000_000:
            raise ValueError('Timestamp too far from current time')
        return v


def validate_event(event_type: str, event_data: dict) -> Optional[BaseModel]:
    """
    Validate an event against its schema
    
    Args:
        event_type: Type of event (keystroke, mouse, app)
        event_data: Raw event data dict
        
    Returns:
        Validated Pydantic model or None if invalid
        
    Raises:
        ValueError: If validation fails
    """
    validators = {
        'keystroke': KeystrokeEvent,
        'mouse': MouseEvent,
        'app': AppEvent
    }
    
    validator_class = validators.get(event_type)
    if not validator_class:
        raise ValueError(f"Unknown event type: {event_type}")
    
    return validator_class(**event_data)
