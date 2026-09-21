
class ProductionRunner:

    def __init__(
        self,
        data_adapter,
        window_manager,
        analyzer,
        risk_engine,
        trace_builder
    ):
        self.data_adapter = data_adapter
        self.window_manager = window_manager
        self.analyzer = analyzer
        self.risk_engine = risk_engine
        self.trace_builder = trace_builder


    def process_candle(self, raw_candle):

        candle = self.data_adapter.normalize(raw_candle)

        window = self.window_manager.add(candle)

        if not window["ready"]:
            return {
                "stage": "WAITING_FOR_WINDOW"
            }

        return {
            "stage": "READY_FOR_ANALYSIS",
            "window_size": window["size"]
        }
