from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from construction_service.domain.messages import BotMessage, UserMessage
from construction_service.domain.state import Turn
from construction_service.infrastructure.llm_client import llm_client
from construction_service.knowledge.providers.base import KnowledgeChunk
from construction_service.history.builder import ChatHistoryBuilder
from construction_service.prompts.loader import load_prompt_template


class KnowledgeResponder:
    async def respond(
            self,
            user_message: UserMessage,
            recent_turns: list[Turn],
            chunks: list[KnowledgeChunk],
    ) -> list[BotMessage]:
        # 准备提示词上下文
        user_message = ChatHistoryBuilder.process_user_message(user_message)
        history = ChatHistoryBuilder.build(recent_turns)
        knowledge_content = "\n\n".join([chunk.content for chunk in chunks])

        # 构造chain
        prompt_text = load_prompt_template("knowledge_respond")
        prompt = PromptTemplate.from_template(
            prompt_text,
            template_format="jinja2"
        )
        chain = prompt | llm_client | StrOutputParser()

        # 运行chain
        response = await chain.ainvoke({
            "user_message": user_message,
            "history": history,
            "knowledge_content": knowledge_content,
        })

        return [BotMessage(text=response)]
