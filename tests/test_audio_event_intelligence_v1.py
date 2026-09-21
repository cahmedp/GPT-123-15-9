
from audio.audio_event_intelligence_v1 import (
    AudioEventDetector,
    VoiceEngine
)


def run():

    detector = AudioEventDetector()
    voice = VoiceEngine()

    print("\n================")
    print("PATTERN ALERT")

    event = detector.detect(
        "PATTERN_READY"
    )

    print(event)
    print(voice.speak(event))


    print("\n================")
    print("WARNING ALERT")

    event = detector.detect(
        "LOW_CONFIDENCE"
    )

    print(event)
    print(voice.speak(event))


if __name__ == "__main__":
    run()
