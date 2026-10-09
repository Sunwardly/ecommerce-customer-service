"""访客权限回归：不调用模型或业务数据库。"""
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from construction_service.api.dependencies import get_dialogue_service
from construction_service.api.router.chat_router import router as chat_router
from construction_service.api.router.visitor_router import router as visitor_router
from construction_service.api.router.avatar_ws_router import router as ws_router
from construction_service.api.visitor_session import COOKIE_NAME, create_session_token, read_session_token
from construction_service.api.demo_access import ACCESS_COOKIE, create_access_token
from construction_service.domain.messages import BotMessage, ProcessResult


class VisitorSessionTests(unittest.TestCase):
    def setUp(self):
        self.key = patch('construction_service.api.visitor_session._signing_key', return_value=b'x' * 32)
        self.key.start()
        self.addCleanup(self.key.stop)
        self.password = patch('construction_service.api.demo_access.access_password', return_value='test-only-access-value')
        self.password.start()
        self.addCleanup(self.password.stop)
        app = FastAPI()
        for router in (visitor_router, chat_router, ws_router):
            app.include_router(router)
        self.service = AsyncMock()
        self.service.load_chat_history.return_value = []
        app.dependency_overrides[get_dialogue_service] = lambda: self.service
        self.a = TestClient(app)
        self.b = TestClient(app)
        for client in (self.a, self.b):
            client.cookies.set(ACCESS_COOKIE, create_access_token())
        self.addCleanup(self.a.close)
        self.addCleanup(self.b.close)

    def test_browsers_get_distinct_identity_and_refresh_keeps_it(self):
        first = self.a.get('/api/visitor/session')
        second = self.b.get('/api/visitor/session')
        self.assertNotEqual(first.json()['sender_id'], second.json()['sender_id'])
        self.assertEqual(first.json(), self.a.get('/api/visitor/session').json())
        self.assertIn('HttpOnly', first.headers['set-cookie'])
        self.assertIn('SameSite=lax', first.headers['set-cookie'])
        self.assertEqual(first.headers['cache-control'], 'no-store')

    def test_new_conversation_rotates_identity(self):
        old = self.a.get('/api/visitor/session').json()['sender_id']
        new = self.a.post('/api/visitor/session').json()['sender_id']
        self.assertNotEqual(old, new)
        self.assertEqual(self.a.get('/api/visitor/session').json()['sender_id'], new)
        self.assertEqual(self.a.get('/api/chat/history', params={'sender_id':old}).status_code, 403)

    def test_history_and_send_require_cookie(self):
        self.assertEqual(self.a.get('/api/chat/history', params={'sender_id':'u1001'}).status_code, 401)
        self.assertEqual(self.a.post('/api/chat', json={'sender_id':'u1001','text':'test'}).status_code, 401)
        self.assertEqual(self.a.post('/api/visitor/session').status_code, 401)
        self.service.load_chat_history.assert_not_awaited()
        self.service.hand_dialogue.assert_not_awaited()

    def test_other_visitors_identity_cannot_be_used(self):
        self.a.get('/api/visitor/session')
        other = self.b.get('/api/visitor/session').json()['sender_id']
        self.assertEqual(self.a.get('/api/chat/history',params={'sender_id':other}).status_code, 403)
        self.assertEqual(self.a.post('/api/chat',json={'sender_id':other,'text':'test'}).status_code, 403)
        self.service.load_chat_history.assert_not_awaited()
        self.service.hand_dialogue.assert_not_awaited()

    def test_sender_is_derived_from_cookie_when_not_provided(self):
        visitor = self.a.get('/api/visitor/session').json()['sender_id']
        self.service.hand_dialogue.return_value = ProcessResult(visitor,'test',[BotMessage(text='ok')])
        response = self.a.post('/api/chat',json={'text':'test'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(self.service.hand_dialogue.call_args.args[0].sender_id, visitor)
        self.a.get('/api/chat/history')
        self.service.load_chat_history.assert_awaited_once_with(visitor)

    def test_tampered_and_expired_cookie_are_rejected(self):
        _, token = create_session_token()
        self.assertIsNone(read_session_token(token[:-1] + ('a' if token[-1] != 'a' else 'b')))
        with patch('construction_service.api.visitor_session.time.time', return_value=10**12):
            self.assertIsNone(read_session_token(token))
        self.a.cookies.set(COOKIE_NAME,'forged')
        self.assertEqual(self.a.get('/api/chat/history').status_code,401)

    def test_cross_site_cannot_rotate_cookie(self):
        self.a.get('/api/visitor/session')
        headers={'sec-fetch-site':'cross-site'}
        self.assertEqual(self.a.get('/api/visitor/session',headers=headers).status_code,403)
        self.assertEqual(self.a.post('/api/visitor/session',headers=headers).status_code,403)

    def test_websocket_requires_cookie_and_rejects_other_sender(self):
        with self.assertRaises(WebSocketDisconnect):
            with self.a.websocket_connect('/ws/avatar/chat'):
                pass
        self.a.get('/api/visitor/session')
        other = self.b.get('/api/visitor/session').json()['sender_id']
        with self.a.websocket_connect('/ws/avatar/chat') as ws:
            ws.send_json({'type':'user_text','sender_id':other,'text':'test'})
            self.assertEqual(ws.receive_json()['type'],'error')
            # 合法身份可省略 sender_id；空文本被正常校验，不触发模型。
            ws.send_json({'type':'user_text','text':''})
            self.assertEqual(ws.receive_json()['type'],'interrupt')
            self.assertEqual(ws.receive_json()['message'],'empty text')

    def test_service_errors_never_echo_or_log_private_exception_content(self):
        self.a.get('/api/visitor/session')
        sentinel = 'sentinel_private_dialogue_not_for_logs'
        for method, path in [('post', '/api/chat'), ('get', '/api/chat/history')]:
            self.service.hand_dialogue.side_effect = RuntimeError(sentinel)
            self.service.load_chat_history.side_effect = RuntimeError(sentinel)
            with self.assertLogs('construction_service.api.router.chat_router', level='WARNING') as logs:
                response = getattr(self.a, method)(path, **({'json': {'text': 'hello'}} if method == 'post' else {}))
            self.assertEqual(response.status_code, 503)
            self.assertNotIn(sentinel, response.text)
            self.assertNotIn(sentinel, '\n'.join(logs.output))


if __name__ == '__main__':
    unittest.main()
