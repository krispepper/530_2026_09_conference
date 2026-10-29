from datetime import date, timedelta
import pytest

# Simulating your deadline logic
def can_register(event_date):
    """Registration allowed only if event is today or in future"""
    today = date.today()
    return event_date >= today

def can_cancel(event_date):
    """Cancellation allowed only if event is today or in future"""
    today = date.today()
    return event_date >= today

# --- YOUR REGISTRATION DEADLINE TESTS ---

def test_registration_blocked_after_deadline():
    """Sprint 4 - Registration deadline: past event cannot be registered"""
    past_event = date.today() - timedelta(days=1)
    assert can_register(past_event) == False

def test_registration_allowed_before_deadline():
    """Sprint 4 - Registration deadline: future event can be registered"""
    future_event = date.today() + timedelta(days=5)
    assert can_register(future_event) == True

def test_registration_allowed_on_deadline_day():
    """Sprint 4 - Registration allowed on the same day as deadline"""
    today_event = date.today()
    assert can_register(today_event) == True

def test_cancellation_blocked_after_deadline():
    """Sprint 4 - Cancellation deadline: past event cannot be canceled"""
    past_event = date.today() - timedelta(days=1)
    assert can_cancel(past_event) == False

def test_cancellation_allowed_before_deadline():
    """Sprint 4 - Cancellation deadline: future event can be canceled"""
    future_event = date.today() + timedelta(days=5)
    assert can_cancel(future_event) == True
