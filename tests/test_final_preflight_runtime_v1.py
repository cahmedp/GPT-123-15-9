
from preflight.final_preflight_runtime_v1 import FinalPreflightRuntime


def run():

    engine = FinalPreflightRuntime()

    print("\n================")
    print("FINAL PREFLIGHT REPORT")

    print(engine.run())


if __name__ == "__main__":
    run()
