"""Permite `python -m discovery_agents <comando>` como atajo de la CLI."""
from __future__ import annotations

import sys

from .interfaces.cli import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
