from construction_service.domain.messages import BotMessage
from construction_service.domain.state import DialogueState
from construction_service.task.action.runner import ActionRunner
from construction_service.task.command.commands import Command
from construction_service.task.flow.flows import FlowsList
from construction_service.task.command.processor import CommandProcessor
from construction_service.task.flow.executor import FlowExecutor


class TaskHandler:

    def __init__(self,
                 flow_list: FlowsList,
                 command_processor: CommandProcessor,
                 executor: FlowExecutor,
                 action_runner: ActionRunner
                 ):
        self.flow_list = flow_list
        self.command_processor = command_processor
        self.flow_executor = executor
        self.action_runner = action_runner

    async def hand(self,
                   state: DialogueState,
                   commands: list[Command]) -> list[BotMessage]:
        # 1. 使用command_processor处理命令
        self.command_processor.run(state, self.flow_list, commands)

        # 2. 使用流程执行器推进流程
        bot_msgs: list[BotMessage] = await self.flow_executor.execute_flow(state, self.flow_list, self.action_runner)

        return bot_msgs
