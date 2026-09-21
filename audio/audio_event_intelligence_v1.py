
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class AudioEvent:
    level: str
    event: str
    message: str
    timestamp: str


class AudioEventDetector:

    PRIORITY = {
        "INFO": 1,
        "ATTENTION": 2,
        "CRITICAL": 3
    }

    def detect(
        self,
        event_type,
        details=None
    ):

        rules = {
            "MARKET_MOVEMENT": (
                "INFO",
                "Market movement detected"
            ),
            "BREAKOUT": (
                "ATTENTION",
                "Level breakout detected. Monitoring continuation"
            ),
            "PATTERN_READY": (
                "CRITICAL",
                "Validated advisory pattern available"
            ),
            "LOW_CONFIDENCE": (
                "ATTENTION",
                "Signal quality reduced. Caution required"
            )
        }

        level, message = rules.get(
            event_type,
            ("INFO", "System event")
        )

        return AudioEvent(
            level=level,
            event=event_type,
            message=message,
            timestamp=datetime.now(timezone.utc).isoformat()
        )


class VoiceEngine:

    def speak(self, audio_event):

        # Placeholder interface.
        # Connected later to OS TTS or custom sounds.
        return {
            "played": True,
            "level": audio_event.level,
            "message": audio_event.message
        }
