from fastapi import FastAPI
from contextlib import asynccontextmanager, suppress
import asyncio
import logging
from construction_service.api.router.chat_router import router
from construction_service.infrastructure.db import init_db_engine, dispose_engine
from construction_service.infrastructure.http_client import init_http_client, dispose_http_client
from construction_service.api.dependencies import init_dialogue_engine
from construction_service.infrastructure.avatar import init_avatar_client
from construction_service.api.router.avatar_router import router as avatar_router
from construction_service.api.router.avatar_ws_router import router as avatar_ws_router
from construction_service.api.router.visitor_router import router as visitor_router
from construction_service.api.router.access_router import router as access_router
from construction_service.api.router.commerce_router import router as commerce_router
from construction_service.api.demo_access import access_password, require_access
from construction_service.config.demo import DEMO_ACCESS_REQUIRED
from construction_service.infrastructure.avatar import expire_chat_session, shutdown_chat_session
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


async def _avatar_cleanup_loop():
    while True:
        await asyncio.sleep(30)
        try:
            await expire_chat_session()
        except Exception:
            logging.getLogger(__name__).warning("数字人过期会话清理失败，将重试")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    在web服务器也即应用启动的时候，会来调用，接着在处理路由之前把初始化的一些信息都可以提前做好
    :param app:
    :return:
    """
    await init_db_engine()
    init_http_client()
    init_dialogue_engine()
    init_avatar_client()
    if DEMO_ACCESS_REQUIRED:
        access_password()
    cleanup = asyncio.create_task(_avatar_cleanup_loop())
    try:
        yield
    finally:
        cleanup.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup
        try:
            await shutdown_chat_session()
        except Exception:
            logging.getLogger(__name__).warning("数字人会话关闭失败，请检查云端实例")

    # 清理资源（应用关闭）
    await  dispose_engine()
    await  dispose_http_client()


app = FastAPI(description="智能客服V1.0", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def safe_validation_error(request: Request, error: RequestValidationError):
    # 登录口令及输入内容不回显在错误响应中。
    return JSONResponse(status_code=422, content={"detail": "请求数据格式不正确，请检查后重试。"})
app.include_router(router)
app.include_router(visitor_router)
app.include_router(access_router)
app.include_router(commerce_router)


@app.middleware("http")
async def protect_demo_api(request: Request, call_next):
    path = request.url.path
    if (path.startswith(("/api/", "/commerce/")) or path in {"/docs", "/redoc", "/openapi.json"}) and path not in {"/api/access/session", "/api/access/login"}:
        try:
            require_access(request)
        except HTTPException as error:
            return JSONResponse(status_code=error.status_code, content={"detail": error.detail}, headers={"Cache-Control": "no-store"})
    return await call_next(request)

app.include_router(avatar_router)
app.include_router(avatar_ws_router)
