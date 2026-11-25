# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from collections import deque
from datetime import datetime, timedelta, UTC


GAP_TIMEOUT = 2.0
MIN_WINDOW = 2


def gap_timeout(config: dict[str, str]) -> timedelta:
    return timedelta(seconds=float(config.get("gap_timeout", GAP_TIMEOUT)))


def GapTracker(start: int, gap_timeout: timedelta):
    def expected(gaps: list[tuple[int, int]], lo: int, hi: int) -> int:
        return hi - lo + 1 - sum(max(0, min(end, hi) - max(start, lo) + 1) for start, end in gaps)

    class _GapTracker:
        def __init__(self, start: int, gap_timeout: timedelta):
            self._recent: deque = deque()
            self._gaps: list[tuple[int, int]] = []
            self._gap_timeout = gap_timeout
            self._safe_id = start
            self._cutoff = start

        def received(self, rid: int, emitted_at: datetime) -> None:
            self._recent.append((rid, emitted_at))

        def accept_gap(self, lo: int, hi: int) -> None:
            self._gaps.append((lo, hi))

        def watching(self) -> bool:
            return bool(self._gaps)

        def count_received(self) -> tuple[int, int, int] | None:
            while self._recent and self._recent[0][1] < datetime.now(UTC) - self._gap_timeout:
                self._safe_id = self._recent.popleft()[0]
            if not self._gaps or self._safe_id <= self._cutoff:
                return None
            lo = self._cutoff + 1
            return expected(self._gaps, lo, self._safe_id), lo, self._safe_id

        def commit(self) -> None:
            if not self._gaps:
                self._cutoff = self._safe_id
            else:
                self._cutoff = max(self._cutoff, self._safe_id - max((self._safe_id - self._cutoff) // 2, MIN_WINDOW))
                self._gaps[:] = [(lo, hi) for lo, hi in self._gaps if hi > self._cutoff]

    return _GapTracker(start, gap_timeout)

