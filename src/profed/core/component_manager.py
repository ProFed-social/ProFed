# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later


import asyncio
import importlib


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
    

def run(config, init=None):
    async def main():
        if init is not None:
            await asyncio.gather(*(fn() for fn in init))

        component_names = config["profed"]["run"]
        components = [Component(name)
                      for name in (component_names
                                   if isinstance(component_names, list) else
                                   component_names.split())]
        await asyncio.gather(*(component(config.get(component.name, {}))
                               for component in components))

    asyncio.run(main())

