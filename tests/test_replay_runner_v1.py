
from adapters.candle_adapter_v1 import CandleAdapter
from runtime.replay_runner_v1 import ReplayRunner


def fake_engine(candle):
    return candle.close > candle.open


def run():

    adapter = CandleAdapter()

    rows = [
        {
            "timestamp":"2026-09-20 10:00:00",
            "open":1.1,
            "high":1.2,
            "low":1.0,
            "close":1.15
        },
        {
            "timestamp":"2026-09-20 10:00:30",
            "open":1.2,
            "high":1.25,
            "low":1.15,
            "close":1.18
        }
    ]

    candles = [
        adapter.normalize(row)
        for row in rows
    ]

    runner = ReplayRunner(fake_engine)

    print("\n================")
    print("REPLAY SESSION #001")
    print(runner.run(candles))


if __name__ == "__main__":
    run()
