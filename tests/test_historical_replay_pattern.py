
from data_engine.historical_replay_loader import (
    HistoricalReplayLoader
)

from validation.pattern_backtester import (
    PatternBacktester
)


def run():

    candles = [
        {"close":100+i}
        for i in range(50)
    ]


    print("\n================")
    print("REPLAY WINDOWS")


    loader = HistoricalReplayLoader(10)

    windows = loader.create_windows(candles)

    print(
        "windows:",
        len(windows)
    )


    print("\n================")
    print("PATTERN TEST")


    result = PatternBacktester().evaluate(
        "BULLISH_EXPANSION",
        [
            "BULLISH_EXPANSION"
            for _ in range(40)
        ]
    )

    print(result)


if __name__ == "__main__":
    run()
