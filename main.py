"""
Personal AI Trading Analyst
Main Entry Point

This file only starts the system.
All logic lives inside core modules.
"""

from core.orchestrator import Analyst


def main() -> None:
    analyst = Analyst()
    analyst.start()


if __name__ == "__main__":
    main()
