"""Independent black-box acceptance checks for the published application API."""

from collections.abc import Callable

from robot_application.application import RobotApplication
from robot_application.models import Event


def effect_values(effects: list[object]) -> list[tuple[str, str]]:
    return [(effect.effect_type, effect.value) for effect in effects]


def assert_no_effects(effects: list[object]) -> None:
    assert effects == [], f"expected no effects, got {effects!r}"


def assert_welcome(effects: list[object]) -> None:
    assert effect_values(effects) == [
        ("ROBOT_ACTION", "wave_hand"),
        ("SPEECH", "欢迎光临"),
    ], f"unexpected welcome effects: {effects!r}"


def assert_farewell(effects: list[object]) -> None:
    assert len(effects) == 1, f"expected one farewell effect, got {effects!r}"
    effect = effects[0]
    assert effect.effect_type == "SPEECH", f"farewell is not speech: {effect!r}"
    assert effect.value.strip(), f"farewell speech is empty: {effect!r}"


def required_timeline() -> None:
    app = RobotApplication()
    steps: list[tuple[Event, Callable[[list[object]], None]]] = [
        (Event("PERSON_ENTERED", 0), assert_welcome),
        (Event("PERSON_ENTERED", 1), assert_no_effects),
        (Event("CONVERSATION_STARTED", 2), assert_no_effects),
        (Event("PERSON_ENTERED", 3), assert_no_effects),
        (Event("CONVERSATION_ENDED", 4), assert_no_effects),
        (Event("PERSON_LEFT", 5), assert_no_effects),
        (Event("TICK", 14), assert_no_effects),
        (Event("TICK", 15), assert_farewell),
        (Event("TICK", 16), assert_no_effects),
        (Event("PERSON_ENTERED", 20), assert_welcome),
    ]

    for event, assertion in steps:
        assertion(app.handle_event(event))


def conversation_suppression_without_catch_up() -> None:
    app = RobotApplication()
    for event in [
        Event("CONVERSATION_STARTED", 0),
        Event("PERSON_ENTERED", 1),
        Event("CONVERSATION_ENDED", 2),
        Event("PERSON_ENTERED", 3),
    ]:
        assert_no_effects(app.handle_event(event))


def meeting_suppression_without_catch_up() -> None:
    app = RobotApplication()
    for event in [
        Event("MEETING_STARTED", 0),
        Event("PERSON_ENTERED", 1),
        Event("MEETING_ENDED", 2),
        Event("PERSON_ENTERED", 3),
    ]:
        assert_no_effects(app.handle_event(event))


def overlapping_busy_states() -> None:
    app = RobotApplication()
    for event in [
        Event("CONVERSATION_STARTED", 0),
        Event("MEETING_STARTED", 1),
        Event("CONVERSATION_ENDED", 2),
        Event("PERSON_ENTERED", 3),
        Event("MEETING_ENDED", 4),
        Event("PERSON_ENTERED", 5),
    ]:
        assert_no_effects(app.handle_event(event))


def brief_absence_return() -> None:
    app = RobotApplication()
    assert_welcome(app.handle_event(Event("PERSON_ENTERED", 0)))
    assert_no_effects(app.handle_event(Event("PERSON_LEFT", 5)))
    assert_no_effects(app.handle_event(Event("TICK", 14)))
    assert_no_effects(app.handle_event(Event("PERSON_ENTERED", 14.5)))
    assert_no_effects(app.handle_event(Event("TICK", 30)))


def configurable_timeout_and_single_farewell() -> None:
    app = RobotApplication(absence_timeout_s=2.5)
    assert_welcome(app.handle_event(Event("PERSON_ENTERED", 0)))
    assert_no_effects(app.handle_event(Event("PERSON_LEFT", 10)))
    assert_no_effects(app.handle_event(Event("TICK", 12.49)))
    assert_farewell(app.handle_event(Event("TICK", 12.5)))
    assert_no_effects(app.handle_event(Event("TICK", 20)))


def busy_timeout_is_not_replayed() -> None:
    app = RobotApplication()
    assert_welcome(app.handle_event(Event("PERSON_ENTERED", 0)))
    assert_no_effects(app.handle_event(Event("PERSON_LEFT", 1)))
    assert_no_effects(app.handle_event(Event("MEETING_STARTED", 2)))
    assert_no_effects(app.handle_event(Event("TICK", 11)))
    assert_no_effects(app.handle_event(Event("MEETING_ENDED", 12)))
    assert_no_effects(app.handle_event(Event("TICK", 13)))
    assert_welcome(app.handle_event(Event("PERSON_ENTERED", 20)))


def snapshot_isolation() -> None:
    app = RobotApplication()
    assert_welcome(app.handle_event(Event("PERSON_ENTERED", 0)))
    before = app.snapshot()
    external_copy = app.snapshot()
    external_copy["reception_active"] = False
    external_copy["absence_started_at"] = 999
    assert app.snapshot() == before, "mutating snapshot changed application state"


CASES = [
    ("required timeline", required_timeline),
    ("conversation suppression", conversation_suppression_without_catch_up),
    ("meeting suppression", meeting_suppression_without_catch_up),
    ("overlapping busy states", overlapping_busy_states),
    ("brief absence return", brief_absence_return),
    ("timeout boundary and deduplication", configurable_timeout_and_single_farewell),
    ("busy timeout has no catch-up", busy_timeout_is_not_replayed),
    ("snapshot isolation", snapshot_isolation),
]


def main() -> int:
    failures = 0
    for name, case in CASES:
        try:
            case()
        except Exception as exc:
            failures += 1
            print(f"[FAIL] {name}: {exc}")
        else:
            print(f"[PASS] {name}")

    passed = len(CASES) - failures
    print(f"\nBlack-box acceptance: {passed}/{len(CASES)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
