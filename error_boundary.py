"""
Central Error Boundary

Unified error handling layer.

Responsibilities:
- Catch component failures
- Classify errors
- Record failures
- Provide safe fallback behavior

Does not change decision logic.
"""


from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import traceback


@dataclass(slots=True)
class ErrorEvent:

    component: str
    error_type: str
    message: str
    timestamp: str
    severity: str



class ErrorBoundary:


    def __init__(self, logger=None):

        self.logger = (
            logger
            or logging.getLogger(
                "ErrorBoundary"
            )
        )

        self.errors: list[ErrorEvent] = []


    def capture(
        self,
        *,
        component: str,
        exc: Exception,
        severity: str = "ERROR",
    ) -> ErrorEvent:


        event = ErrorEvent(

            component=component,

            error_type=type(exc).__name__,

            message=str(exc),

            timestamp=datetime.now(
                timezone.utc
            ).isoformat(),

            severity=severity,
        )


        self.errors.append(event)


        self.logger.exception(
            "Component failure [%s]: %s",
            component,
            exc,
        )


        return event



    def execute(
        self,
        *,
        component: str,
        operation,
        fallback=None,
    ):

        try:

            return operation()


        except Exception as exc:

            self.capture(
                component=component,
                exc=exc,
            )

            return fallback



    def summary(self):

        return {

            "total_errors": len(
                self.errors
            ),

            "components": list(
                {
                    e.component
                    for e in self.errors
                }
            ),
        }
