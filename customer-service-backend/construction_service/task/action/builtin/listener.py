from typing import Any

from construction_service.domain.state import DialogueState
from construction_service.task.action.base import Action, ActionResult


class ActionListener(Action):

    name = "action_listen"

    async def run(self,
            state: DialogueState,
            action_args: dict[str, Any]) -> ActionResult:
        pass

