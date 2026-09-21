from __future__ import annotations


class VoiceEngine:
    """
    Converts explanation text into a voice-ready script.

    Actual TTS provider integration will be added later.
    """

    def build_script(
        self,
        *,
        title: str,
        summary: str,
        reasons: list[str] | None = None,
    ) -> str:

        lines = [
            title,
            summary,
        ]

        if reasons:
            lines.append(
                "Main reasons:"
            )

            lines.extend(
                reasons[:5]
            )

        return ". ".join(lines)