# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone
from profed.identity import status_id


EARLY = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
LATE = datetime(2026, 1, 1, 11, 0, 0, tzinfo=timezone.utc)


def test_status_id_is_numeric():
    assert status_id(EARLY, 1, own=True).isdigit()


def test_status_id_fits_into_64_bits():
    assert int(status_id(LATE, 2 ** 18 - 1, own=True)) < 2 ** 64


def test_status_id_sorts_by_time_across_origins():
    own_late = int(status_id(LATE, 1000, own=True))
    incoming_early = int(status_id(EARLY, 1, own=False))

    assert own_late > incoming_early


def test_status_id_sorts_by_sequence_within_one_millisecond():
    first = int(status_id(EARLY, 7, own=True))
    second = int(status_id(EARLY, 8, own=True))

    assert second > first


def test_status_id_distinguishes_origins_on_equal_time_and_sequence():
    assert status_id(EARLY, 7, own=True) != status_id(EARLY, 7, own=False)


def test_status_id_is_deterministic():
    assert status_id(EARLY, 7, own=True) == status_id(EARLY, 7, own=True)

