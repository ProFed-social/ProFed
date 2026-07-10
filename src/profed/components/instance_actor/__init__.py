# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from .reconciler import run_reconcile


async def InstanceActor(config: dict) -> None:
    await run_reconcile(config)

