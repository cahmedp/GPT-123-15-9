
from runtime.engine_runtime_phase_v1 import EngineRuntime


def run():

    engine = EngineRuntime()

    engine.process_cycle(0.82, True)
    engine.process_cycle(0.78, True)
    engine.process_cycle(0.40, False)

    engine.update_knowledge()

    print("\n================")
    print("ENGINE RUNTIME REPORT")

    print(engine.report())


if __name__ == "__main__":
    run()
