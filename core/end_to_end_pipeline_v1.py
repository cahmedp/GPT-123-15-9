
from dataclasses import dataclass


@dataclass
class PipelineExecution:
    stage: str
    approved: bool
    pattern: str
    confidence: float
    trace: list
    blockers: list


class EndToEndPipeline:

    def __init__(
        self,
        data_adapter,
        window_manager,
        analyzer,
        validator,
        risk_engine,
        trace_builder
    ):
        self.data_adapter = data_adapter
        self.window_manager = window_manager
        self.analyzer = analyzer
        self.validator = validator
        self.risk_engine = risk_engine
        self.trace_builder = trace_builder


    def process(self, raw_candle):

        trace = []

        candle = self.data_adapter.normalize(raw_candle)
        trace.append("DATA_NORMALIZED")

        window = self.window_manager.add(candle)

        if not window["ready"]:
            return PipelineExecution(
                "WAITING_WINDOW",
                False,
                None,
                0.0,
                trace,
                []
            )

        trace.append("WINDOW_READY")

        analysis = self.analyzer.run(window["candles"])
        trace.append("HYBRID_CREATED")

        validation = self.validator.validate(analysis)
        trace.append("VALIDATION_DONE")

        risk = self.risk_engine.evaluate(validation)

        if not risk.allowed:
            return PipelineExecution(
                "RISK_BLOCK",
                False,
                analysis.pattern,
                analysis.confidence,
                trace,
                risk.blockers
            )

        trace.append("APPROVED")

        return PipelineExecution(
            "EXECUTION_READY",
            True,
            analysis.pattern,
            analysis.confidence,
            trace,
            []
        )
