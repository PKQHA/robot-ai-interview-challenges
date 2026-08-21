import pytest

from robot_application.application import RobotApplication
from robot_application.models import Effect, Event


WELCOME_EFFECTS = [
    Effect("ROBOT_ACTION", "wave_hand", "new_reception"),
    Effect("SPEECH", "欢迎光临", "new_reception"),
]
FAREWELL_EFFECTS = [
    Effect("SPEECH", "感谢光临，欢迎下次再来", "absence_confirmed")
]


def test_first_entry_welcomes_and_repeated_entry_does_not():
    app = RobotApplication()

    assert app.handle_event(Event("PERSON_ENTERED", 0)) == WELCOME_EFFECTS
    assert app.handle_event(Event("PERSON_ENTERED", 1)) == []


@pytest.mark.parametrize(
    ("started", "ended"),
    [
        ("CONVERSATION_STARTED", "CONVERSATION_ENDED"),
        ("MEETING_STARTED", "MEETING_ENDED"),
    ],
)
def test_busy_period_suppresses_welcome_without_catch_up(started, ended):
    app = RobotApplication()

    assert app.handle_event(Event(started, 0)) == []
    assert app.handle_event(Event("PERSON_ENTERED", 1)) == []
    assert app.handle_event(Event(ended, 2)) == []
    assert app.handle_event(Event("PERSON_ENTERED", 3)) == []


def test_conversation_and_meeting_suppression_can_overlap():
    app = RobotApplication()

    assert app.handle_event(Event("CONVERSATION_STARTED", 0)) == []
    assert app.handle_event(Event("MEETING_STARTED", 1)) == []
    assert app.handle_event(Event("CONVERSATION_ENDED", 2)) == []
    assert app.handle_event(Event("PERSON_ENTERED", 3)) == []
    assert app.handle_event(Event("MEETING_ENDED", 4)) == []
    assert app.handle_event(Event("PERSON_ENTERED", 5)) == []


def test_farewell_occurs_at_timeout_only_once():
    app = RobotApplication(absence_timeout_s=10.0)

    app.handle_event(Event("PERSON_ENTERED", 0))
    assert app.handle_event(Event("PERSON_LEFT", 5)) == []
    assert app.handle_event(Event("TICK", 14.999)) == []
    assert app.handle_event(Event("TICK", 15)) == FAREWELL_EFFECTS
    assert app.handle_event(Event("TICK", 16)) == []


def test_return_before_timeout_cancels_farewell_and_does_not_welcome_again():
    app = RobotApplication()

    assert app.handle_event(Event("PERSON_ENTERED", 0)) == WELCOME_EFFECTS
    assert app.handle_event(Event("PERSON_LEFT", 5)) == []
    assert app.handle_event(Event("TICK", 14)) == []
    assert app.handle_event(Event("PERSON_ENTERED", 14.5)) == []
    assert app.handle_event(Event("TICK", 20)) == []


def test_entry_after_confirmed_absence_starts_new_reception():
    app = RobotApplication()

    assert app.handle_event(Event("PERSON_ENTERED", 0)) == WELCOME_EFFECTS
    assert app.handle_event(Event("PERSON_LEFT", 1)) == []
    assert app.handle_event(Event("TICK", 11)) == FAREWELL_EFFECTS
    assert app.handle_event(Event("PERSON_ENTERED", 20)) == WELCOME_EFFECTS


def test_absence_confirmed_while_busy_is_not_sent_later():
    app = RobotApplication()

    app.handle_event(Event("PERSON_ENTERED", 0))
    app.handle_event(Event("PERSON_LEFT", 1))
    assert app.handle_event(Event("CONVERSATION_STARTED", 2)) == []
    assert app.handle_event(Event("TICK", 11)) == []
    assert app.handle_event(Event("CONVERSATION_ENDED", 12)) == []
    assert app.handle_event(Event("TICK", 13)) == []
    assert app.handle_event(Event("PERSON_ENTERED", 20)) == WELCOME_EFFECTS


def test_required_timeline():
    app = RobotApplication()

    timeline = [
        (Event("PERSON_ENTERED", 0), WELCOME_EFFECTS),
        (Event("PERSON_ENTERED", 1), []),
        (Event("CONVERSATION_STARTED", 2), []),
        (Event("PERSON_ENTERED", 3), []),
        (Event("CONVERSATION_ENDED", 4), []),
        (Event("PERSON_LEFT", 5), []),
        (Event("TICK", 14), []),
        (Event("TICK", 15), FAREWELL_EFFECTS),
        (Event("TICK", 16), []),
        (Event("PERSON_ENTERED", 20), WELCOME_EFFECTS),
    ]

    assert [app.handle_event(event) for event, _ in timeline] == [
        expected for _, expected in timeline
    ]


def test_snapshot_is_detached_from_internal_state():
    app = RobotApplication()
    app.handle_event(Event("PERSON_ENTERED", 0))
    app.handle_event(Event("PERSON_LEFT", 5))

    snapshot = app.snapshot()
    snapshot["reception_active"] = False
    snapshot["absence_started_at"] = 999

    assert app.snapshot() == {
        "absence_timeout_s": 10.0,
        "reception_active": True,
        "absence_started_at": 5,
        "conversation_active": False,
        "meeting_active": False,
    }
