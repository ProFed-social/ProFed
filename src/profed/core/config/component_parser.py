from typing import Any, Dict
from copy import copy
import inspect

class ConfigError(Exception):
    pass


class _parse_iteration:
    def __init__(self, raw, parsed) -> None:
        self._progress = False
        self._raw = copy(raw)
        self._parsed = copy(parsed)

        for section in raw.keys():
            parse_fn = self._parse_function(section)
            can_parse, expected_params = self._parameters_available(parse_fn)

            if can_parse:
                raw_section = self._raw.pop(section)
                self._parsed[section] = parse_fn(raw_section,
                                                 **{arg: self._parsed[arg]
                                                    for arg in expected_params})
                self._progress = True

    def _parse_function(self, section):
        parse_fn = lambda cfg: cfg
        try:
            mod = __import__(f"profed.adapters.{section}.config", fromlist=["parse"])
            parse_fn = getattr(mod, "parse", parse_fn)
        except ImportError:
            pass

        return parse_fn

    def _parameters_available(self, parse_fn):
            signature = inspect.signature(parse_fn)
            expected = [p.name
                        for p in signature.parameters.values()
                        if p.default == inspect.Parameter.empty and
                           p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD][1:]
            return all(p in self._parsed for p in expected), expected

    def __call__(self):
        return self._raw, self._parsed

    def __bool__(self) -> bool:
        return self._progress


def components_from_raw(raw: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
    parsed = {}

    while raw:
        iteration = _parse_iteration(raw, parsed)

        if iteration:
            raw, parsed = iteration()
        else:
            raise ConfigError(f"Circular or missing dependency in config sections: {raw.keys()}")

    return parsed
