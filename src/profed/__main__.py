# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

from functools import partial 

logging.basicConfig(level=logging.WARNING,
                    format="%(levelname)s %(name)s %(message)s")

from profed.core.config import config
from profed.core.component_manager import run
from profed.core.message_bus import init_message_bus
from profed.topics import names


STANDARD_COMPONENTS = ["api",
                       "user_activities",
                       "activity_delivery",
                       "follow_handler",
                       "accept_handler"]


if __name__ == "__main__":
    config.set_defaults({"profed": {"run": STANDARD_COMPONENTS}})
    cfg = config()

    level = cfg.get("logging", {}).get("level", "INFO")
    logging.getLogger().setLevel(getattr(logging, level.upper()))

    run(cfg, [partial(init_message_bus, names())])

