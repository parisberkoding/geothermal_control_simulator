"""
Event Logger
Tracks all system events with timestamps
"""
from datetime import datetime
from typing import List, Tuple
from enum import Enum

class EventType(Enum):
    """Event severity levels"""
    INFO = "INFO"
    WARNING = "WARNING"
    ALARM = "ALARM"
    CRITICAL = "CRITICAL"
    CONTROL = "CONTROL"

class EventLogger:
    """Logger for system events"""
    
    def __init__(self, max_events=1000):
        """
        Initialize event logger
        
        Args:
            max_events: Maximum number of events to keep in memory
        """
        self.events: List[Tuple[datetime, EventType, str]] = []
        self.max_events = max_events
    
    def log(self, event_type: EventType, message: str):
        """
        Log an event
        
        Args:
            event_type: Type of event
            message: Event message
        """
        timestamp = datetime.now()
        self.events.append((timestamp, event_type, message))
        
        # Keep only last max_events
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
    
    def get_recent_events(self, count=50) -> List[str]:
        """
        Get recent events formatted as strings
        
        Args:
            count: Number of recent events to return
            
        Returns:
            List of formatted event strings
        """
        recent = self.events[-count:] if len(self.events) > count else self.events
        formatted = []
        
        for timestamp, event_type, message in reversed(recent):
            time_str = timestamp.strftime("%H:%M:%S")
            formatted.append(f"[{time_str}] {event_type.value}: {message}")
        
        return formatted
    
    def get_alarms(self) -> List[str]:
        """Get all alarm-level events"""
        alarms = [
            (timestamp, message) 
            for timestamp, event_type, message in self.events
            if event_type in [EventType.ALARM, EventType.CRITICAL]
        ]
        
        formatted = []
        for timestamp, message in alarms:
            time_str = timestamp.strftime("%H:%M:%S")
            formatted.append(f"[{time_str}] {message}")
        
        return formatted
    
    def clear(self):
        """Clear all events"""
        self.events.clear()
        self.log(EventType.INFO, "Event log cleared")

# Test
if __name__ == '__main__':
    logger = EventLogger()
    logger.log(EventType.INFO, "System started")
    logger.log(EventType.WARNING, "Pressure rising")
    logger.log(EventType.ALARM, "High pressure detected")
    logger.log(EventType.CONTROL, "Valve #1 adjusted to 50%")
    
    print("Recent events:")
    for event in logger.get_recent_events(10):
        print(event)