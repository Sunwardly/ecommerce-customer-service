from pathlib import Path

from construction_service.chitchat.responder import ChitChatResponder
from construction_service.engine.dialogue_engine import DialogueEngine
from construction_service.knowledge.responder import KnowledgeResponder
from construction_service.plan.planner import TurnPlanner
from construction_service.task.handler import TaskHandler
from construction_service.knowledge.handler import KnowledgeHandler
from construction_service.plan.validator import TurnPlanValidator
from construction_service.chitchat.handler import ChitChatHandler
from construction_service.task.flow.loader import FlowLoader
from construction_service.knowledge.intents import KNOWLEDGE_INTENTS
from construction_service.clarify.responder import ClarifyResponser
from construction_service.task.command.processor import CommandProcessor
from construction_service.task.flow.executor import FlowExecutor
from construction_service.task.action.builder import build_action_runner
from construction_service.knowledge.providers.registry import KnowledgeProviderRegistry
from construction_service.knowledge.providers.knowledge import ProductAPIProvider, OrderAPIProvider, FAQProvider, RAGProvider

PROJECT_ROOT_DIR = Path(__file__).resolve().parents[2]
FLOW_CONFIG_DIR = PROJECT_ROOT_DIR / "flow_config"
FLOW_CONFIG_FILE = ["system_flows.yml", "user_flows.yml"]


def build_dialogue_engine():
    flow_list = FlowLoader().load_many_yaml(
        [FLOW_CONFIG_DIR / file for file in FLOW_CONFIG_FILE])  # flow_list是两个yml中的流程(系统流程、业务流程)

    return DialogueEngine(
        planner=TurnPlanner(),
        task_handler=TaskHandler(flow_list=flow_list,
                                 command_processor=CommandProcessor(),
                                 executor=FlowExecutor(),
                                 action_runner=build_action_runner()
                                 ),
        turn_plan_validator=TurnPlanValidator(),
        knowledge_handler=KnowledgeHandler(
            knowledge_intents=KNOWLEDGE_INTENTS,
            knowledge_register=KnowledgeProviderRegistry(providers=[
                ProductAPIProvider(),
                OrderAPIProvider(),
                FAQProvider(),
                RAGProvider()
            ]),
            knowledge_responder=KnowledgeResponder()
        ),
        chitchat_handler=ChitChatHandler(chitchat_responder=ChitChatResponder()),
        clarify_responder=ClarifyResponser()

    )
