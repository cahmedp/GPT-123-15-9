
from runtime.runtime_session_tracking_v1 import (
    RuntimeSessionManager
)


def run():

    manager = RuntimeSessionManager()

    session = manager.start_session()

    print("\n================")
    print("RUNTIME SESSION")

    print(session)


if __name__ == "__main__":
    run()
