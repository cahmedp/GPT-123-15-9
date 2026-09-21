from communication.explanation_engine import ExplanationEngine
from communication.voice_engine import VoiceEngine


explanation = ExplanationEngine().explain(
    action="WAIT",
    confidence=0.62,
    uncertainty=0.55,
    reasons=[
        "High market noise",
        "Multi timeframe conflict",
    ],
)


print(
    explanation.as_dict()
)


voice = VoiceEngine().build_script(
    title=explanation.title,
    summary=explanation.summary,
    reasons=list(explanation.reasons),
)


print(voice)