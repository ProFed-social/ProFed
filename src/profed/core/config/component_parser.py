from typing import Any, Dict, Sequence
from copy import copy, deepcopy
import inspect

class ConfigError(Exception):
    pass


class parse_list:
    def __init__(self, runlist: Sequence[str]):
        self.parsers = {}

        rl = [r for r in runlist]
        newfound = True
        while newfound:
           newfound, parsers = self._find_parsers(rl)

           self.parsers.update(parsers)

           newfound = {nf for nf in newfound if nf not in rl}
           if len(newfound) == 0:
               break
           rl += newfound

    def _find_parse(self, component: str):
        try:
            mod = __import__(f"profed.adapters.{component}.config", fromlist=["parse"])
            return getattr(mod, "parse", None)
        except ImportError:
            return None

    def _extract_expected_sections(self, parse_fn):
            signature = inspect.signature(parse_fn)
            return [p.name
                    for p in signature.parameters.values()
                    if p.default == inspect.Parameter.empty and
                       p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD][1:]

    def _find_parsers(self, runlist: Sequence[str]):
        parsers = {}
        newfound = set()
        for component in runlist:
            parse_fn = self._find_parse(component)
            if parse_fn is None:
                continue
            expected = self._extract_expected_sections(parse_fn)

            newfound = newfound | set(expected)
            parsers[component] = (parse_fn, expected)
        return list(newfound), parsers


    def parse_all(self, raw):
        parsed = {}
        to_call_parsers = {name for name in self.parsers.keys()}

        while to_call_parsers:
            called = set()
            for p in to_call_parsers:
                parse_fn, expected = self.parsers[p]
                if all(n in parsed for n in expected):
                    parsed[p] = parse_fn(raw[p], **{arg: parsed[arg] for arg in expected})
                    called.add(p)
            if not called:
                raise ConfigError(f"Circular or missing dependency in config sections: {to_call_parsers}")
            to_call_parsers = {p for p in to_call_parsers if p not in called}

        return parsed


def components_from_raw(raw: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
    parsers = parse_list(raw["profed"]["run"].split())
    parsed = deepcopy(raw)
    parsed.update(parsers.parse_all(raw))
    return parsed

