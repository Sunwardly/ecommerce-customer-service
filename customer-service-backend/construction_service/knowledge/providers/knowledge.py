import asyncio
import json
from typing import Any

from construction_service.domain.state import DialogueState
from construction_service.knowledge.providers.base import KnowledgeProvider, KnowledgeChunk
from construction_service.services.demo_commerce_service import fetch_demo_object, DemoObjectDenied


class ProductAPIProvider(KnowledgeProvider):
    provider_id = 'api.product'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        product_id = state.focused_object.id
        try:
            data: dict[str, Any] = await self._get_product_info_by_id(product_id)
        except DemoObjectDenied:
            return [KnowledgeChunk(content="只能查询当前演示列表中的商品，请选择演示商品。")]
        text = json.dumps(data, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"商品信息:\n{text}")]

    async def _get_product_info_by_id(self, product_id: str) -> dict[str, Any]:
        return (await fetch_demo_object("products", product_id))["data"]



class OrderAPIProvider(KnowledgeProvider):
    provider_id = 'api.order'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        focused_object = state.focused_object
        order_number = focused_object.id

        try:
            order_payload, logistics_payload = await asyncio.gather(
                self._fetch_order(order_number), self._fetch_logistics(order_number),
            )
        except DemoObjectDenied:
            return [KnowledgeChunk(content="只能查询当前演示列表中的订单，请选择演示订单。")]

        return [
            KnowledgeChunk(
                content="订单与物流信息：\n"
                        + json.dumps(
                    {
                        "order_number": order_number,
                        "order": order_payload,
                        "logistics": logistics_payload,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        ]

    async def _fetch_order(self, order_number) -> dict[str, Any]:
        return (await fetch_demo_object("orders", order_number))["data"]

    async def _fetch_logistics(self, order_number) -> dict[str, Any]:
        return (await fetch_demo_object("orders", order_number, "logistics")).get("data", {})



class FAQProvider(KnowledgeProvider):
    """
    FAQ知问题集文档查询的能力接入进来
    """
    provider_id = 'faq.default'


    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        return [KnowledgeChunk(content="未检索到相关问题")]



class RAGProvider(KnowledgeProvider):
    """
    RAG知识库的能力接入进来
    """
    provider_id = 'rag.default'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        # TODO (通过HTTP请求 接入知识库暴露的知识检索接口)
        return [KnowledgeChunk(content="未检索到相关信息")]
