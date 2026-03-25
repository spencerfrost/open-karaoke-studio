"""Unit tests for app/utils/events.py — EventBus, JobEvent, and convenience functions."""
from unittest.mock import MagicMock, patch

import pytest

from app.utils.events import (
    Event,
    EventBus,
    JobEvent,
    event_bus,
    publish_job_event,
    subscribe_to_job_events,
)


@pytest.fixture(autouse=True)
def clean_event_bus():
    """Clear all EventBus subscribers before and after each test."""
    event_bus.clear_subscribers()
    yield
    event_bus.clear_subscribers()


# ---------------------------------------------------------------------------
# JobEvent
# ---------------------------------------------------------------------------


class TestJobEvent:
    def test_stores_job_id_and_data(self):
        e = JobEvent(job_id="j1", job_data={"status": "completed"})
        assert e.job_id == "j1"
        assert e.job_data["status"] == "completed"

    def test_name_is_job_updated(self):
        e = JobEvent(job_id="j1", job_data={})
        assert e.name == "job_updated"

    def test_was_created_defaults_to_false(self):
        e = JobEvent(job_id="j1", job_data={})
        assert e.was_created is False

    def test_was_created_set_to_true(self):
        e = JobEvent(job_id="j1", job_data={}, was_created=True)
        assert e.was_created is True

    def test_data_dict_contains_expected_keys(self):
        e = JobEvent(job_id="j1", job_data={"status": "pending"})
        assert e.data["job_id"] == "j1"
        assert e.data["job_data"]["status"] == "pending"
        assert e.data["was_created"] is False

    def test_none_job_data_becomes_empty_dict(self):
        e = JobEvent(job_id="j1", job_data=None)
        assert e.job_data == {}


# ---------------------------------------------------------------------------
# EventBus singleton
# ---------------------------------------------------------------------------


class TestEventBusSingleton:
    def test_same_instance_returned(self):
        a = EventBus()
        b = EventBus()
        assert a is b


# ---------------------------------------------------------------------------
# EventBus.subscribe / publish
# ---------------------------------------------------------------------------


class TestEventBusSubscribePublish:
    def test_handler_called_on_publish(self):
        handler = MagicMock()
        event_bus.subscribe("test_event", handler)
        event = Event(name="test_event", data={})
        event_bus.publish(event)
        handler.assert_called_once_with(event)

    def test_multiple_handlers_all_called(self):
        h1, h2 = MagicMock(), MagicMock()
        event_bus.subscribe("test_event", h1)
        event_bus.subscribe("test_event", h2)
        event = Event(name="test_event", data={})
        event_bus.publish(event)
        h1.assert_called_once()
        h2.assert_called_once()

    def test_no_subscribers_does_not_raise(self):
        event = Event(name="no_such_event", data={})
        event_bus.publish(event)  # should not raise

    def test_failing_handler_does_not_prevent_other_handlers(self):
        bad_handler = MagicMock(side_effect=RuntimeError("boom"))
        good_handler = MagicMock()
        event_bus.subscribe("test_event", bad_handler)
        event_bus.subscribe("test_event", good_handler)
        event_bus.publish(Event(name="test_event", data={}))
        good_handler.assert_called_once()

    def test_handler_not_called_for_different_event(self):
        handler = MagicMock()
        event_bus.subscribe("event_a", handler)
        event_bus.publish(Event(name="event_b", data={}))
        handler.assert_not_called()


# ---------------------------------------------------------------------------
# EventBus.unsubscribe
# ---------------------------------------------------------------------------


class TestEventBusUnsubscribe:
    def test_unsubscribed_handler_not_called(self):
        handler = MagicMock()
        event_bus.subscribe("test_event", handler)
        event_bus.unsubscribe("test_event", handler)
        event_bus.publish(Event(name="test_event", data={}))
        handler.assert_not_called()

    def test_unsubscribe_nonexistent_handler_no_error(self):
        handler = MagicMock()
        event_bus.unsubscribe("test_event", handler)  # should not raise

    def test_unsubscribe_handler_not_in_subscribed_event_logs_warning(self):
        """Handler not found in an existing event list triggers ValueError path (lines 98-99)."""
        other_handler = MagicMock()
        event_bus.subscribe("test_event", other_handler)
        missing_handler = MagicMock()
        # "test_event" exists in subscribers but missing_handler is not in it
        event_bus.unsubscribe("test_event", missing_handler)  # should not raise

    def test_unsubscribe_from_unknown_event_no_error(self):
        event_bus.unsubscribe("totally_unknown", MagicMock())  # should not raise


# ---------------------------------------------------------------------------
# EventBus.clear_subscribers
# ---------------------------------------------------------------------------


class TestEventBusClearSubscribers:
    def test_clear_specific_event(self):
        handler = MagicMock()
        event_bus.subscribe("test_event", handler)
        event_bus.clear_subscribers("test_event")
        event_bus.publish(Event(name="test_event", data={}))
        handler.assert_not_called()

    def test_clear_specific_event_leaves_others(self):
        h1, h2 = MagicMock(), MagicMock()
        event_bus.subscribe("event_a", h1)
        event_bus.subscribe("event_b", h2)
        event_bus.clear_subscribers("event_a")
        event_bus.publish(Event(name="event_b", data={}))
        h2.assert_called_once()

    def test_clear_all_events(self):
        h1, h2 = MagicMock(), MagicMock()
        event_bus.subscribe("event_a", h1)
        event_bus.subscribe("event_b", h2)
        event_bus.clear_subscribers()
        event_bus.publish(Event(name="event_a", data={}))
        event_bus.publish(Event(name="event_b", data={}))
        h1.assert_not_called()
        h2.assert_not_called()


# ---------------------------------------------------------------------------
# publish_job_event
# ---------------------------------------------------------------------------


class TestPublishJobEvent:
    def test_publishes_job_event_to_bus(self):
        handler = MagicMock()
        event_bus.subscribe("job_updated", handler)
        publish_job_event("job-1", {"status": "completed"})
        handler.assert_called_once()
        received_event = handler.call_args[0][0]
        assert isinstance(received_event, JobEvent)
        assert received_event.job_id == "job-1"

    def test_passes_was_created_flag(self):
        handler = MagicMock()
        event_bus.subscribe("job_updated", handler)
        publish_job_event("job-2", {}, was_created=True)
        received = handler.call_args[0][0]
        assert received.was_created is True


# ---------------------------------------------------------------------------
# subscribe_to_job_events
# ---------------------------------------------------------------------------


class TestSubscribeToJobEvents:
    def test_handler_called_for_job_event(self):
        handler = MagicMock()
        subscribe_to_job_events(handler)
        publish_job_event("job-1", {"status": "pending"})
        handler.assert_called_once()
        assert isinstance(handler.call_args[0][0], JobEvent)

    def test_handler_not_called_for_plain_event(self):
        handler = MagicMock()
        subscribe_to_job_events(handler)
        # Publish a plain Event (not JobEvent) with name "job_updated"
        event_bus.publish(Event(name="job_updated", data={}))
        handler.assert_not_called()
