from construction_service.task.action.register import ActionRegister
from construction_service.task.action.base import  ActionResult,ActionCall
from construction_service.domain.state import  DialogueState

class ActionRunner:
    """
    负责使用对应的Action(action_name---->action--->action的run方法)
    """
    def __init__(self, registry: ActionRegister) -> None:
        self.registry = registry

    async def run(self, action_call: ActionCall, state: DialogueState) -> ActionResult:
        action_name = action_call.action_name
        action = self.registry.get(action_name)
        return await action.run(state, action_call.action_kwargs)

