"""演示业务数据边界，供对话动作、知识查询和公网网关共同使用。"""
from urllib.parse import quote
from construction_service.config.demo import DEMO_USER_ID
from construction_service.config.settings import settings
from construction_service.infrastructure import http_client


class DemoObjectDenied(ValueError):
    pass


async def _get(path: str) -> dict:
    response = await http_client.http_client.get(f"{settings.commerce_api_base_url.rstrip('/')}{path}")
    response.raise_for_status()
    return response.json()


async def fetch_demo_list(kind: str) -> dict:
    if kind not in {"orders", "products"}:
        raise DemoObjectDenied("演示对象类型不允许")
    return await _get(f"/users/{DEMO_USER_ID}/{kind}")


async def fetch_demo_object(kind: str, object_id: str, section: str | None = None) -> dict:
    if section not in {None, "status", "logistics"} or (kind == "products" and section):
        raise DemoObjectDenied("演示对象接口不允许")
    payload = await fetch_demo_list(kind)
    key = "order_id" if kind == "orders" else "product_id"
    ids = {item.get(key) for item in payload.get("data", {}).get(kind, [])}
    if object_id not in ids:
        raise DemoObjectDenied("只能访问当前演示列表中的对象")
    suffix = f"/{section}" if section else ""
    return await _get(f"/{kind}/{quote(object_id, safe='')}{suffix}")
