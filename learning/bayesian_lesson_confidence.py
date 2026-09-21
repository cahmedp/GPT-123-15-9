
from dataclasses import dataclass

@dataclass
class BayesianLessonResult:
    name: str
    samples: int
    matches: int
    posterior: float
    strength: str
    reason: str


class BayesianLessonConfidence:

    def __init__(self, prior_success=0.5, prior_strength=20):
        self.prior_success = prior_success
        self.prior_strength = prior_strength

    def evaluate(self, name, samples, matches):

        posterior = (
            matches + self.prior_success * self.prior_strength
        ) / (samples + self.prior_strength)

        posterior = round(posterior, 3)

        if samples < 30:
            strength = "WEAK_EVIDENCE"
            reason = "Small sample protection"
        elif posterior >= 0.75:
            strength = "STRONG_EVIDENCE"
            reason = "Posterior confidence threshold reached"
        elif posterior < 0.45:
            strength = "NEGATIVE_EVIDENCE"
            reason = "Poor posterior performance"
        else:
            strength = "UNCERTAIN"
            reason = "Needs more evidence"

        return BayesianLessonResult(
            name,
            samples,
            matches,
            posterior,
            strength,
            reason
        )
