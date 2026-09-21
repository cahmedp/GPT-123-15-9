
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class RuntimeSession:
    session_id: str
    started_at: str
    version: str
    mode: str


class RuntimeSessionManager:

    def start_session(self):

        now = datetime.now(timezone.utc)

        session_id = (
            "RUN_" +
            now.strftime("%Y%m%d_%H%M%S")
        )

        return RuntimeSession(
            session_id=session_id,
            started_at=now.isoformat(),
            version="1.0 Experimental",
            mode="ADVISORY_ONLY"
        )
