
from console.terminal_intelligence_console_v3 import TerminalIntelligenceConsoleV3


def run():
    console = TerminalIntelligenceConsoleV3()
    state = console.update()

    print("\n================")
    print("LIVE DASHBOARD V3")
    print(console.render(state))


if __name__ == "__main__":
    run()
