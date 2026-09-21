from __future__ import annotations

import json
import threading
from pathlib import Path

import pyttsx3


class VoiceAlert:

    def __init__(self):

        self.state_file = Path(
            "storage/state/voice_state.json"
        )

        self.state_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self._last_action = self._load_state()

        self.engine = pyttsx3.init()

        self.engine.setProperty(
            "rate",
            160
        )


    def check(self, action: str):

        action = str(action).upper()

        if action == self._last_action:
            return

        previous = self._last_action

        self._last_action = action

        self._save_state(
            action
        )

        if previous is None:
            return

        self._announce_transition(
            previous,
            action
        )


    def _load_state(self):

        if not self.state_file.exists():
            return None

        try:
            data = json.loads(
                self.state_file.read_text(
                    encoding="utf-8"
                )
            )

            return data.get(
                "last_action"
            )

        except Exception:
            return None


    def _save_state(
        self,
        action: str
    ):

        self.state_file.write_text(
            json.dumps(
                {
                    "last_action": action
                },
                indent=4
            ),
            encoding="utf-8"
        )


    def _announce_transition(
        self,
        old: str,
        new: str
    ):

        messages = {

            ("WAIT", "BUY"):
                "Buy signal detected",

            ("WAIT", "SELL"):
                "Sell signal detected",

            ("BUY", "SELL"):
                "Direction changed from buy to sell",

            ("SELL", "BUY"):
                "Direction changed from sell to buy",
        }


        message = messages.get(
            (old, new)
        )


        if not message:
            return


        threading.Thread(
            target=self._speak,
            args=(message,),
            daemon=True
        ).start()


    def _speak(
        self,
        text: str
    ):

        self.engine.say(
            text
        )

        self.engine.runAndWait()