
from dataclasses import dataclass


@dataclass
class PersistentPipelineResult:
    stage: str
    saved: dict
    approved: bool
    blockers: list


class PersistentOrchestrator:

    def __init__(
        self,
        decision_repository,
        knowledge_repository,
        feedback_repository
    ):
        self.decision_repository = decision_repository
        self.knowledge_repository = knowledge_repository
        self.feedback_repository = feedback_repository


    def save_decision(self, trace):

        self.decision_repository.save(trace)

        return "DECISION_SAVED"


    def save_knowledge(self, knowledge):

        self.knowledge_repository.save(knowledge)

        return "KNOWLEDGE_SAVED"


    def save_feedback(
        self,
        pattern,
        prediction,
        actual,
        result,
        reward
    ):

        self.feedback_repository.save(
            pattern,
            prediction,
            actual,
            result,
            reward
        )

        return "FEEDBACK_SAVED"


    def finalize(
        self,
        trace,
        knowledge,
        feedback
    ):

        saved = {
            "decision": self.save_decision(trace),
            "knowledge": self.save_knowledge(knowledge),
            "feedback": self.save_feedback(**feedback)
        }

        return PersistentPipelineResult(
            stage="PERSISTENT_COMPLETE",
            saved=saved,
            approved=True,
            blockers=[]
        )
