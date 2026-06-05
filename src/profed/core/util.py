# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later


def extract_component_names(component_names):
    return (component_names
            if isinstance(component_names, list) else
            component_names.split())

