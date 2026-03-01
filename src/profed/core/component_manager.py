# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later


import os
import asyncio
import importlib
from typing import Dict, Any, Optional


class ComponentError(Exception):
    pass


class Component:
    def __init__(self, name):
        self.name = name

    def __call__(self, cfg) -> None:
        try:
            mod = importlib.import_module(f"profed.adapters.{self.name}")
            component = getattr(mod, "".join(n.capitalize() for n in self.name.split("_")))
            asyncio.run(component(cfg))
        except Exception as e:
            raise ComponentError(f"Error in component {self.name}: {e}")
    

class Process:
    def __init__(self, cmp: Component, cfg):
        self.pid = os.fork()
        if self.pid == 0:
            # child process
            cmp(cfg)
            os._exit(0)

    def wait(self) -> None:
        os.waitpid(self.pid, 0)


def run(config: Dict[str, Any]) -> None:
    components = list(config["profed"]["run"].split())
    main = components.pop(0)

    if main is None:
        raise IndexError("No components to run configured")

    processes = [Process(Component(name), config.get(name, {}))
                 for name in components]

    Component(main)(config[main])

    for p in processes:
        p.wait()

