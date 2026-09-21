
from dataclasses import dataclass


@dataclass
class ReplayResult:
    candles_processed: int
    windows_created: int
    analyses: int
    validations: int
    blocked: int
    status: str


class ReplayRunner:

    def __init__(self, engine=None):
        self.engine = engine


    def run(self, candles):

        windows = 0
        analyses = 0
        validations = 0
        blocked = 0

        for candle in candles:

            # Pipeline hook:
            # candle -> window -> agents -> hybrid -> validation
            windows += 1

            if self.engine:
                result = self.engine(candle)

                analyses += 1

                if result:
                    validations += 1
                else:
                    blocked += 1

        return ReplayResult(
            candles_processed=len(candles),
            windows_created=windows,
            analyses=analyses,
            validations=validations,
            blocked=blocked,
            status="REPLAY_COMPLETED"
        )
