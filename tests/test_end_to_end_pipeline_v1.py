
from core.end_to_end_pipeline_v1 import EndToEndPipeline


class Adapter:
    def normalize(self, x):
        return x


class Window:
    def __init__(self):
        self.items=[]

    def add(self,c):
        self.items.append(c)
        return {
            "ready": len(self.items)>=2,
            "candles":self.items
        }


class Analysis:
    pattern="BULLISH_EXPANSION"
    confidence=0.82


class Analyzer:
    def run(self,candles):
        return Analysis()


class Validation:
    pass


class Validator:
    def validate(self,a):
        return Validation()


class Risk:
    allowed=True
    blockers=[]


class RiskEngine:
    def evaluate(self,v):
        return Risk()


def run():

    pipeline = EndToEndPipeline(
        Adapter(),
        Window(),
        Analyzer(),
        Validator(),
        RiskEngine(),
        None
    )

    print("\n================")
    print("FIRST CANDLE")

    print(
        pipeline.process({"close":100})
    )

    print("\n================")
    print("FULL PIPELINE")

    print(
        pipeline.process({"close":101})
    )


if __name__=="__main__":
    run()
