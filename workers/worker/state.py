"""Per-camera dwell/revisit state machine.

For each ``person_global_id`` seen by a camera we track:

* ``first_seen_at`` of the current continuous presence.
* ``last_seen_at`` (so we know when to close out a dwell).
* A list of recent appearance start times, trimmed to the configured rolling
  window, used for the revisit threshold.

We emit at most one DWELL event per continuous presence (latched) and at most
one REVISIT event per appearance once the threshold is crossed.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

GAP_FOR_NEW_APPEARANCE_SEC = 30.0


@dataclass
class PersonState:
    first_seen_at: float
    last_seen_at: float
    appearance_starts: list[float] = field(default_factory=list)
    dwell_emitted: bool = False
    revisit_emitted_for_appearance: bool = False


@dataclass
class ThresholdEvent:
    kind: str  # "DWELL" or "REVISIT"
    person_global_id: str
    start_time: float
    end_time: float
    duration_sec: int | None = None
    appearance_count: int | None = None


class CameraStateMachine:
    def __init__(self, dwell_limit_sec: int, count_limit: int, count_window_sec: int):
        self.dwell_limit_sec = dwell_limit_sec
        self.count_limit = count_limit
        self.count_window_sec = count_window_sec
        self._states: dict[str, PersonState] = {}

    def update_seen(self, pgid: str, now: float) -> ThresholdEvent | None:
        st = self._states.get(pgid)
        emitted: ThresholdEvent | None = None

        if st is None:
            st = PersonState(first_seen_at=now, last_seen_at=now, appearance_starts=[now])
            self._states[pgid] = st
        elif now - st.last_seen_at > GAP_FOR_NEW_APPEARANCE_SEC:
            st.first_seen_at = now
            st.dwell_emitted = False
            st.revisit_emitted_for_appearance = False
            st.appearance_starts.append(now)

        st.last_seen_at = now

        cutoff = now - self.count_window_sec
        st.appearance_starts = [t for t in st.appearance_starts if t >= cutoff]

        dwell_secs = now - st.first_seen_at
        if not st.dwell_emitted and dwell_secs >= self.dwell_limit_sec:
            st.dwell_emitted = True
            emitted = ThresholdEvent(
                kind="DWELL",
                person_global_id=pgid,
                start_time=st.first_seen_at,
                end_time=now,
                duration_sec=int(dwell_secs),
            )

        appearance_count = len(st.appearance_starts)
        if (
            not st.revisit_emitted_for_appearance
            and appearance_count >= self.count_limit
        ):
            st.revisit_emitted_for_appearance = True
            emitted = ThresholdEvent(
                kind="REVISIT",
                person_global_id=pgid,
                start_time=st.appearance_starts[0],
                end_time=now,
                appearance_count=appearance_count,
            )
        return emitted

    def gc(self, max_age_sec: float = 3600.0) -> None:
        now = time.time()
        for pgid in list(self._states):
            if now - self._states[pgid].last_seen_at > max_age_sec:
                del self._states[pgid]
