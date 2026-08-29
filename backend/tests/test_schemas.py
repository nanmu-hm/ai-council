from app.schemas import EventType, ProviderEvent


def test_event_types_are_stable_strings():
    assert EventType.MODEL_DELTA.value == "model.delta"


def test_provider_event_defaults():
    event = ProviderEvent(EventType.MODEL_COMPLETED, "test", "demo")
    assert event.text == ""
    assert event.error is None
