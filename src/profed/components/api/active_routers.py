# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from typing import Any, Dict, List
 
 
def narrow_deactivate_routers(prefix: str,
                              deactivate: List[str]) -> List[str]:
    return [name[len(prefix):]
            for name in deactivate
            if name.startswith(prefix)]
 
 
def get_active(named_items: Dict[str, Any],
               deactivate: List[str]) -> List[Any]:
    return [item
            for name, item in named_items.items()
            if name not in deactivate]

