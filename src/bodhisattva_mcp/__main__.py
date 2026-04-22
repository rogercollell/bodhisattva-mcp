"""Entry point: `bodhisattva-mcp` or `python -m bodhisattva_mcp`."""

from __future__ import annotations

import asyncio
import sys

from bodhisattva_mcp import __version__
from bodhisattva_mcp.server import run


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] in ("--version", "-V"):
        print(f"bodhisattva-mcp {__version__}")
        return
    asyncio.run(run())


if __name__ == "__main__":
    main()
