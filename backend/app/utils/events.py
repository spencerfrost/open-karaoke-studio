# backend/app/utils/events.py
"""
Simple event system for decoupling application components.

This prevents cyclic imports by allowing models to emit events
without directly importing business logic modules.
"""

import logging
from typing import Any, Callable, Dict, List
from dataclasses import dataclass
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Base event class for all application events."""

    name: str
    data: Dict[str, Any]


@dataclass
class JobEvent(Event):
    """Event emitted when job state changes."""

    job_id: str = ""
    job_data: Dict[str, Any] = None
    was_created: bool = False

    def __init__(
        self, job_id: str, job_data: Dict[str, Any], was_created: bool = False
    ):
        """Initialize JobEvent with proper parent initialization."""
        self.job_id = job_id
        self.job_data = job_data or {}
        self.was_created = was_created

        # Initialize parent Event class
        super().__init__(
            name="job_updated",
            data={
                "job_id": self.job_id,
                "job_data": self.job_data,
                "was_created": self.was_created,
            },
        )


class EventBus:
    """
    Simple event bus for publishing and subscribing to events.

    Thread-safe singleton implementation for application-wide event handling.
    """

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._subscribers: Dict[str, List[Callable]] = {}
                    cls._instance._subscribers_lock = Lock()
        return cls._instance

    def subscribe(self, event_name: str, handler: Callable[[Event], None]) -> None:
        """
        Subscribe to events of a specific type.

        Args:
            event_name: Name of the event to subscribe to
            handler: Function to call when event is published
        """
        with self._subscribers_lock:
            if event_name not in self._subscribers:
                self._subscribers[event_name] = []
            self._subscribers[event_name].append(handler)
            logger.debug(f"Subscribed handler to '{event_name}' event")

    def unsubscribe(self, event_name: str, handler: Callable[[Event], None]) -> None:
        """
        Unsubscribe from events of a specific type.

        Args:
            event_name: Name of the event to unsubscribe from
            handler: Handler function to remove
        """
        with self._subscribers_lock:
            if event_name in self._subscribers:
                try:
                    self._subscribers[event_name].remove(handler)
                    logger.debug(f"Unsubscribed handler from '{event_name}' event")
                except ValueError:
                    logger.warning(f"Handler not found for '{event_name}' event")

    def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event: Event to publish
        """
        with self._subscribers_lock:
            subscribers = self._subscribers.get(event.name, []).copy()

        if subscribers:
            logger.debug(
                f"Publishing '{event.name}' event to {len(subscribers)} subscribers"
            )
            for handler in subscribers:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(
                        f"Error in event handler for '{event.name}': {e}", exc_info=True
                    )
        else:
            logger.debug(f"No subscribers for '{event.name}' event")

    def clear_subscribers(self, event_name: str = None) -> None:
        """
        Clear all subscribers for an event type, or all events if no name provided.

        Args:
            event_name: Specific event to clear, or None to clear all
        """
        with self._subscribers_lock:
            if event_name:
                self._subscribers.pop(event_name, None)
                logger.debug(f"Cleared all subscribers for '{event_name}' event")
            else:
                self._subscribers.clear()
                logger.debug("Cleared all event subscribers")


# Global event bus instance
event_bus = EventBus()


# Convenience functions for common operations
def publish_job_event(
    job_id: str, job_data: Dict[str, Any], was_created: bool = False
) -> None:
    """
    Convenience function to publish job events.
    Args:
        job_id: ID of the job
        job_data: Job data dictionary
        was_created: Whether this is a new job creation
    """
    event = JobEvent(job_id=job_id, job_data=job_data, was_created=was_created)
    print(f"📢 Publishing job event: {job_id} - created={was_created} - status={job_data.get('status', 'unknown')}")
    event_bus.publish(event)


def subscribe_to_job_events(handler: Callable[[JobEvent], None]) -> None:
    """
    Convenience function to subscribe to job events.

    Args:
        handler: Function to handle job events
    """

    def wrapper(event: Event) -> None:
        if isinstance(event, JobEvent):
            handler(event)

    event_bus.subscribe("job_updated", wrapper)
