from typing import Any
from construction_service.services.demo_commerce_service import fetch_demo_object



def _extract_data(result: dict | None) -> dict | None:
    data = result.get("data") if isinstance(result, dict) else None
    return data if isinstance(data, dict) else None


async def fetch_order(order_id: str) -> dict | None:
    try:
        return _extract_data(await fetch_demo_object("orders", order_id))
    except Exception:
        return None


async def fetch_logistics(order_id: str) -> dict | None:
    try:
        return _extract_data(await fetch_demo_object("orders", order_id, "logistics"))
    except Exception:
        return None


async def fetch_product(product_id: str) -> dict | None:
    try:
        return _extract_data(await fetch_demo_object("products", product_id))
    except Exception:
        return None


def _build_order_summary(payload: dict[str, Any]) -> str:
    parts = []
    if payload.get("amount"):
        parts.append(f"订单金额 ¥{payload['amount']}")
    items = payload.get("items") or []
    if items:
        titles = [str(item.get("title") or "").strip() for item in items[:2] if item.get("title")]
        if titles:
            parts.append("商品：" + "、".join(titles))
    return "。".join(parts)if parts else ""
