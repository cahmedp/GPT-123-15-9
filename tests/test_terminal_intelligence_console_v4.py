
from console.terminal_intelligence_console_v4 import (
    TerminalIntelligenceConsoleV4
)


def run():

    console = TerminalIntelligenceConsoleV4()

    console.push_event(
        "MARKET",
        "Movement detected",
        "INFO"
    )

    console.push_event(
        "HYBRID",
        "Pattern validated",
        "CRITICAL"
    )

    print("\n================")
    print("RUNTIME CONSOLE V4")

    print(
        console.render(
            console.snapshot()
        )
    )


if __name__ == "__main__":
    run()
