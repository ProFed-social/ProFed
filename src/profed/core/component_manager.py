# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later


import os
import asyncio
import importlib
from typing import List, Dict, Any, Optional, Callable


class ComponentError(Exception):
    pass


class Component:
    def __init__(self, name: str):
        self.name = name
        self.entry = None
        try:
            mod = importlib.import_module(f"profed.components.{self.name}")
            self.entry = getattr(mod, "".join(n.capitalize() for n in self.name.split("_")))
        except Exception as e:
            raise ComponentError(f"Error in component {self.name}: {e}")
 
    async def __call__(self, cfg) -> None:
        if self.entry is not None:
            await (self.entry(cfg))
    

def run(config: Dict[str, Any], init=None) -> None:
    async def init_all(i):
        await asyncio.gather(*i)
    if init is not None:
        asyncio.run(init_all(init))

    component_names = list(config["profed"]["run"].split())
    components = [Component(name) for name in component_names]
    async def main():
        await asyncio.gather(*[component(config.get(component.name, {}))
                               for component in components])
    asyncio.run(main())

