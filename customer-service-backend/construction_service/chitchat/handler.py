from construction_service.chitchat.responder import ChitChatResponder
from construction_service.domain.messages import BotMessage


class ChitChatHandler:
    def __init__(self, chitchat_responder: ChitChatResponder):
        self.chitchat_responder = chitchat_responder

    async def hand(self, state) -> list[BotMessage]:
        return await self.chitchat_responder.respond(state)
