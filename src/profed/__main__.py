# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

 
logging.basicConfig(level=logging.WARNING,
                    format="%(levelname)s %(name)s %(message)s")
 

from profed.core.config import config
from profed.core.component_manager import run
from profed.core.message_bus import init_message_bus


if __name__ == "__main__":
    cfg = config()
    level = cfg.get("logging", {}).get("level", "INFO")
    logging.getLogger().setLevel(getattr(logging, level.upper()))
    run(cfg, [init_message_bus])

