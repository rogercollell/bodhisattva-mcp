"""Entry point: `bodhisattva-mcp` or `python -m bodhisattva_mcp`."""

import asyncio

from bodhisattva_mcp.server import run


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
