"""
Startup logic for ProFed.

Loads configuration, parses component configs, and starts configured components.
"""

from profed.core.config import config
from profed.core.component_manager import run


if __name__ == "__main__":
    run(config())
