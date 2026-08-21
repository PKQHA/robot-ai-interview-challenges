from .models import Effect, Event


class RobotApplication:
    """Handle greeting events for one reception-area attendance session."""

    def __init__(self, absence_timeout_s: float = 10.0):
        self._absence_timeout_s = absence_timeout_s
        self._reception_active = False
        self._absence_started_at: float | None = None
        self._conversation_active = False
        self._meeting_active = False

    def handle_event(self, event: Event) -> list[Effect]:
        """Apply one event and return only the effects created by that event."""
        if event.event_type == "CONVERSATION_STARTED":
            self._conversation_active = True
            return []

        if event.event_type == "CONVERSATION_ENDED":
            self._conversation_active = False
            return []

        if event.event_type == "MEETING_STARTED":
            self._meeting_active = True
            return []

        if event.event_type == "MEETING_ENDED":
            self._meeting_active = False
            return []

        if event.event_type == "PERSON_ENTERED":
            is_new_reception = not self._reception_active
            self._reception_active = True
            self._absence_started_at = None

            if is_new_reception and not self._is_busy():
                return [
                    Effect("ROBOT_ACTION", "wave_hand", "new_reception"),
                    Effect("SPEECH", "欢迎光临", "new_reception"),
                ]
            return []

        if event.event_type == "PERSON_LEFT":
            if self._reception_active and self._absence_started_at is None:
                self._absence_started_at = event.timestamp
            return []

        if event.event_type == "TICK":
            return self._handle_tick(event.timestamp)

        return []

    def snapshot(self) -> dict[str, object]:
        """Return a detached view of the current application state."""
        return {
            "absence_timeout_s": self._absence_timeout_s,
            "reception_active": self._reception_active,
            "absence_started_at": self._absence_started_at,
            "conversation_active": self._conversation_active,
            "meeting_active": self._meeting_active,
        }

    def _handle_tick(self, timestamp: float) -> list[Effect]:
        if not self._reception_active or self._absence_started_at is None:
            return []

        absence_duration = timestamp - self._absence_started_at
        if absence_duration < self._absence_timeout_s:
            return []

        self._reception_active = False
        self._absence_started_at = None

        if self._is_busy():
            return []

        return [
            Effect(
                "SPEECH",
                "感谢光临，欢迎下次再来",
                "absence_confirmed",
            )
        ]

    def _is_busy(self) -> bool:
        return self._conversation_active or self._meeting_active
