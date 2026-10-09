import unittest
from unittest.mock import AsyncMock, Mock, patch

import httpx

from construction_service.domain.messages import BotMessage, FocusedObject, MessageType, UserMessage
from construction_service.domain.state import DialogueState
from construction_service.engine.dialogue_engine import DialogueEngine
from construction_service.services.demo_commerce_service import DemoObjectDenied
from construction_service.services.order_overview_service import describe_order
from construction_service.task.command.commands import SetSlotsCommand
from construction_service.task.flow.flows import FlowsList


class OrderOverviewTests(unittest.IsolatedAsyncioTestCase):
    def order(self):
        return {'data': {'order_id': 'demo-order', 'status': '运输中', 'status_desc': '包裹正在运输',
                         'amount': '149.00', 'created_at': '2026-10-08T12:00:00',
                         'items': [{'title': '测试水壶', 'quantity': 1, 'price': '149.00'}]}}

    async def test_details_and_latest_logistics_use_business_data(self):
        logistics = {'data': {'order_id': 'demo-order', 'logistics_company': '演示快递',
                             'tracking_number': 'demo-tracking', 'status_desc': '运输中',
                             'traces': [{'time': '2026-10-08T10:00:00', 'desc': '旧记录'},
                                        {'time': '2026-10-09T10:00:00', 'desc': '最新记录'}]}}
        with patch('construction_service.services.order_overview_service.fetch_demo_object',
                   new_callable=AsyncMock, side_effect=[self.order(), logistics]) as fetch:
            text, available = await describe_order('demo-order')
        self.assertTrue(available)
        for expected in ('测试水壶 × 1', '¥149.00', '运输中', '2026-10-08 12:00:00', '最新记录', 'demo-tracking'):
            self.assertIn(expected, text)
        self.assertNotIn('旧记录', text)
        self.assertEqual(fetch.await_count, 2)

    async def test_no_logistics_does_not_invent_delivery(self):
        error = httpx.HTTPStatusError('not found', request=httpx.Request('GET', 'http://demo'),
                                     response=httpx.Response(404))
        with patch('construction_service.services.order_overview_service.fetch_demo_object',
                   new_callable=AsyncMock, side_effect=[self.order(), error]):
            text, available = await describe_order('demo-order')
        self.assertTrue(available)
        self.assertIn('暂无物流记录', text)
        self.assertNotIn('预计', text)

    async def test_logistics_failure_keeps_order_details(self):
        with patch('construction_service.services.order_overview_service.fetch_demo_object',
                   new_callable=AsyncMock, side_effect=[self.order(), RuntimeError('private upstream')]):
            text, available = await describe_order('demo-order')
        self.assertTrue(available)
        self.assertIn('测试水壶', text)
        self.assertIn('暂时查询失败', text)
        self.assertNotIn('private upstream', text)

    async def test_denied_and_failed_orders_do_not_fetch_logistics(self):
        for error, expected in [(DemoObjectDenied(), '不在当前演示列表'), (RuntimeError('private'), '详情暂时查询失败')]:
            with patch('construction_service.services.order_overview_service.fetch_demo_object',
                       new_callable=AsyncMock, side_effect=error) as fetch:
                text, available = await describe_order('demo-order')
            self.assertFalse(available)
            self.assertIn(expected, text)
            self.assertNotIn('private', text)
            fetch.assert_awaited_once()

    def engine(self):
        self.task = Mock(flow_list=FlowsList())
        self.task.hand = AsyncMock(return_value=[BotMessage(text='继续业务流程')])
        self.clarify = Mock(respond=AsyncMock(return_value=[BotMessage(text='商品澄清')]))
        return DialogueEngine(Mock(), Mock(), self.task, Mock(), Mock(), self.clarify)

    async def test_order_card_returns_overview_and_commits_history(self):
        engine = self.engine()
        state = DialogueState(sender_id='visitor')
        message = UserMessage(sender_id='visitor', message_id='message', type=MessageType.OBJECT,
                              object=FocusedObject(id='demo-order', type='order', title='untrusted title', attributes={'amount': '0'}))
        with patch('construction_service.engine.dialogue_engine.describe_order', new_callable=AsyncMock,
                   return_value=('服务端订单详情', True)) as describe:
            result = await engine.hand_message(message, state)
        describe.assert_awaited_once_with('demo-order')
        self.assertEqual(result.messages[0].text, '服务端订单详情')
        self.assertEqual(state.current_session().turns[-1].bot_messages[0].text, '服务端订单详情')
        self.clarify.respond.assert_not_awaited()
        self.task.hand.assert_not_awaited()

    async def test_collecting_order_still_advances_task_after_overview(self):
        engine = self.engine()
        state = DialogueState(sender_id='visitor')
        command = SetSlotsCommand(command='set_slots', slots={'order_number': 'demo-order'})
        with patch.object(engine, '_resolve_object_command', return_value=command), \
             patch('construction_service.engine.dialogue_engine.describe_order', new_callable=AsyncMock,
                   return_value=('订单详情', True)):
            result = await engine._hand_obj_msg(FocusedObject(id='demo-order', type='order'), state, FlowsList())
        self.assertEqual([item.text for item in result], ['订单详情', '继续业务流程'])
        self.task.hand.assert_awaited_once_with(state, commands=[command])

    async def test_product_behavior_is_unchanged(self):
        engine = self.engine()
        with patch('construction_service.engine.dialogue_engine.describe_order', new_callable=AsyncMock) as describe:
            result = await engine._hand_obj_msg(FocusedObject(id='demo-product', type='product'),
                                                 DialogueState(sender_id='visitor'), FlowsList())
        self.assertEqual(result[0].text, '商品澄清')
        describe.assert_not_awaited()
