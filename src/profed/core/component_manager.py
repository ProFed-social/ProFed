# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later


import asyncio
import importlib

from contextlib import asynccontextmanager

from profed.core.persistence.schemata import reset_schemata

class ComponentError(Exception):
    pass


class Component:
    def __init__(self, name: str):
        self.name = name
        self.entry = None
        try:
            mod = importlib.import_module(f"profed.components.{self.name}")
            self.entry = getattr(mod, "".join(n.capitalize() for n in self.name.split("_")))
            self.using_schemata = getattr(mod, "using_schemata", [])
        except Exception as e:
            raise ComponentError(f"Error in component {self.name}: {e}")
 
    async def __call__(self, cfg) -> None:
        await reset_schemata(self.using_schemata, cfg)

        if self.entry is not None:
            await (self.entry(cfg))
    

def run(config, init=None):
    @asynccontextmanager
    async def _lifecycle(init):
        shutdowns = ([sd
                      for sd in await asyncio.gather(*(fn() for fn in init))
                      if sd is not None]
                     if init is not None else
                     [])

        yield

        print(shutdowns)
        if shutdowns:
            await asyncio.gather(*shutdowns)

    async def main():
        async with _lifecycle(init):
            component_names = config["profed"]["run"]
            components = [Component(name)
                          for name in (component_names
                                       if isinstance(component_names, list) else
                                       component_names.split())]

            await asyncio.gather(*(component(config.get(component.name, {}))
                                   for component in components))

    asyncio.run(main())
 
