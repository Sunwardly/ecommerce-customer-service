import uuid
import logging
from fastapi import APIRouter, Response, HTTPException
from construction_service.api.dependencies import DialogueServiceDep
from construction_service.api.schemas import ChatRequest, ChatResponse, ChatBotMessage, ChatObject,ChatMessageResponse
from construction_service.domain.messages import ProcessResult, UserMessage, MessageType, FocusedObject,ChatHistoryMessage
from construction_service.api.visitor_session import VisitorSessionDep, check_sender_id


router = APIRouter()
logger = logging.getLogger(__name__)


def unavailable(error: Exception) -> HTTPException:
    # Exception messages may embed LLM output, SQL parameters or upstream credentials.
    logger.warning("Dialogue service unavailable (%s)", type(error).__name__)
    return HTTPException(status_code=503, detail="对话服务暂时不可用，请稍后重试。")


@router.get("/hello")
async def hello():
    return {"success": "ok"}


@router.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(chat_request: ChatRequest,
                        service: DialogueServiceDep,
                        visitor: VisitorSessionDep):
    check_sender_id(chat_request.sender_id, visitor)
    chat_request = chat_request.model_copy(update={"sender_id": visitor})
    # 1. 将接口数据模型转成领域数据模型
    user_message = _build_user_message(chat_request)

    # 2. 注入service使用
    try:
        process_result: ProcessResult = await service.hand_dialogue(user_message)
    except Exception as error:
        raise unavailable(error) from None

    # 3. 将领域数据模型转成接口数据模型
    chat_response = _build_chat_response(process_result)

    return chat_response


def _build_user_message(chat_request: ChatRequest) -> UserMessage:
    """
    将接口数据模型转成领域数据模型UserMessage
    :param chat_request:
    :return:
    """
    return UserMessage(
        sender_id=chat_request.sender_id,
        message_id=str(uuid.uuid4()),
        type=MessageType.OBJECT if chat_request.object else MessageType.TEXT,
        text=chat_request.text,
        object=FocusedObject(
            id=chat_request.object.id,
            type=chat_request.object.type,
            title=chat_request.object.title,
            attributes=chat_request.object.attributes,
        ) if chat_request.object else None
    )


def _build_chat_response(process_result: ProcessResult) -> ChatResponse:
    """
    将领域数据模型转成接口数据模型ChatResponse
    :param process_result:
    :return:
    """

    return ChatResponse(
        sender_id=process_result.sender_id,
        message_id=process_result.message_id,
        messages=[ChatBotMessage(text=bot_message.text,
                                 object=ChatObject(
                                     id=bot_message.object.id,
                                     type=bot_message.object.type,
                                     title=bot_message.object.title,
                                     attributes=bot_message.object.attributes,
                                 ) if bot_message.object else None) for bot_message in process_result.messages]
    )



@router.get("/api/chat/history", response_model=ChatMessageResponse)
async def chat_history_endpoint(response: Response, service: DialogueServiceDep,
                                visitor: VisitorSessionDep,
                                sender_id: str | None = None) -> ChatMessageResponse:

    check_sender_id(sender_id, visitor)
    response.headers["Cache-Control"] = "no-store"

    try:
        chat_message_response: list[ChatHistoryMessage] = await service.load_chat_history(visitor)
    except Exception as error:
        raise unavailable(error) from None

    return ChatMessageResponse(sender_id=visitor, messages=chat_message_response)
