# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later


import asyncio
import importlib

from contextlib import asynccontextmanager

from profed.core.persistence.schemata import reset_schemata
from profed.core.util import extract_component_names

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

        if shutdowns:
            await asyncio.gather(*shutdowns)

    async def main():
        async with _lifecycle(init):
            components = [Component(name)
                          for name in extract_component_names(config["profed"]["run"])]

            await asyncio.gather(*(component(config.get(component.name, {}))
                                   for component in components))

    asyncio.run(main())


def collect_component_hooks(component_names, hook):
    def component_module(name):
        try:
            return importlib.import_module(f"profed.components.{name}")
        except Exception as e:
            raise ComponentError(f"Error in component {name}: {e}")

    return {name: fn
            for name, fn in ((name, getattr(component_module(name), hook, None))
                             for name in extract_component_names(component_names))
            if fn is not None}

