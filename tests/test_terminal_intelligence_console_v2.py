
from console.terminal_intelligence_console_v2 import (
    TerminalIntelligenceConsoleV2
)


def run():

    console = TerminalIntelligenceConsoleV2()

    state = console.update()

    print("\n================")
    print("LIVE CONSOLE V2")

    print(console.render(state))


if __name__ == "__main__":
    run()
