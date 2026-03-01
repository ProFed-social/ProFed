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
        self.entry = None
        try:
            mod = importlib.import_module(f"profed.adapters.{self.name}")
            self.entry = getattr(mod, "".join(n.capitalize() for n in self.name.split("_")))
        except Exception as e:
            raise ComponentError(f"Error in component {self.name}: {e}")
 
    def __call__(self, cfg) -> None:
        if self.entry is not None:
            asyncio.run(self.entry(cfg))
    

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

    components = [Component(name) for name in components]
    processes = [Process(component, config.get(component.name, {}))
                 for component in components]

    Component(main)(config[main])

    for p in processes:
        p.wait()

