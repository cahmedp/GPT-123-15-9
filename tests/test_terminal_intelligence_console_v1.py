
from console.terminal_intelligence_console_v1 import (
    TerminalIntelligenceConsole
)


def run():

    console = TerminalIntelligenceConsole()

    snapshot = console.build_snapshot()

    print(console.render(snapshot))


if __name__ == "__main__":
    run()
