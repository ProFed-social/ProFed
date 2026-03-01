# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import sys
from .component_parser import components_from_raw, ConfigError
from .raw import raw_config, force_reload_raw

class parsed_config:
    ConfigError = ConfigError

    def __init__(self):
        self._config = None

    def reset(self):
        self._config = components_from_raw(force_reload_raw())

    def __call__(self):
        if not self._config:
            self._config = components_from_raw(raw_config())
        return self._config

    
config = parsed_config()

