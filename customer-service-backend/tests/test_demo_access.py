"""演示入口、业务范围和数字人租约回归；不调用真实云服务或数据库。"""
import asyncio
import time
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from construction_service.api.app import protect_demo_api
from construction_service.api.router.access_router import router as access_router
from construction_service.api.router.visitor_router import router as visitor_router
from construction_service.api.router.commerce_router import router as commerce_router
from construction_service.api.router.avatar_router import router as avatar_router
from construction_service.api.demo_access import ACCESS_COOKIE, _attempts, valid_access_token
from construction_service.infrastructure import avatar
from construction_service.services import demo_commerce_service as commerce
from construction_service.task.action.customer.shared import fetch_order
from construction_service.knowledge.providers.knowledge import ProductAPIProvider
from construction_service.domain.state import DialogueState
from construction_service.domain.messages import FocusedObject


class DemoAccessTests(unittest.TestCase):
    def setUp(self):
        _attempts.clear()
        gate = patch('construction_service.api.demo_access.DEMO_ACCESS_REQUIRED', True)
        gate.start()
        self.addCleanup(gate.stop)
        for name, value in [
            ('construction_service.api.visitor_session._signing_key', b'x' * 32),
            ('construction_service.api.demo_access.access_password', 'test-only-demo-access'),
            ('construction_service.api.router.access_router.access_password', 'test-only-demo-access'),
        ]:
            mock = patch(name, return_value=value)
            mock.start()
            self.addCleanup(mock.stop)
        for name, value in [('LINGMOU_AVAILABLE',True),('_session',None),('_session_owner',None),('_lease_deadline',0)]:
            mock=patch.object(avatar,name,value)
            mock.start()
            self.addCleanup(mock.stop)
        self.create = patch.object(avatar,'_do_create',return_value={'sessionId':'test-cloud-session','rtcParams':{}}).start()
        self.close = patch.object(avatar,'_close_session_ids',return_value=1).start()
        self.addCleanup(patch.stopall)
        app=FastAPI()
        app.middleware('http')(protect_demo_api)
        for router in (access_router,visitor_router,commerce_router,avatar_router): app.include_router(router)
        self.a=TestClient(app)
        self.b=TestClient(app)
        self.addCleanup(self.a.close)
        self.addCleanup(self.b.close)

    def admit(self, client):
        self.assertEqual(client.post('/api/access/login',json={'password':'test-only-demo-access'}).status_code,200)
        return client.get('/api/visitor/session').json()['sender_id']

    def test_gate_protects_visitor_business_and_docs(self):
        self.assertFalse(self.a.get('/api/access/session').json()['authenticated'])
        for path in ('/api/visitor/session','/api/avatar/session','/commerce/users/u1001/orders','/docs','/openapi.json'):
            self.assertEqual(self.a.get(path).status_code,401)
        self.admit(self.a)
        self.assertTrue(self.a.get('/api/access/session').json()['authenticated'])

    def test_wrong_password_and_attempt_limit(self):
        for _ in range(10):
            self.assertEqual(self.a.post('/api/access/login',json={'password':'wrong'}).status_code,401)
        self.assertEqual(self.a.post('/api/access/login',json={'password':'wrong'}).status_code,429)

    def test_access_cookie_tampering_expiry_and_password_rotation(self):
        self.admit(self.a)
        token=self.a.cookies.get(ACCESS_COOKIE)
        self.assertTrue(valid_access_token(token))
        self.assertFalse(valid_access_token(token[:-1]+('a' if token[-1]!='a' else 'b')))
        with patch('construction_service.api.demo_access.time.time',return_value=10**12):
            self.assertFalse(valid_access_token(token))
        with patch('construction_service.api.demo_access.access_password',return_value='different-test-password'):
            self.assertFalse(valid_access_token(token))

    def test_business_writes_and_other_user_are_denied_without_io(self):
        self.admit(self.a)
        with patch.object(commerce,'_get',new_callable=AsyncMock) as read:
            self.assertEqual(self.a.get('/commerce/users/other/orders').status_code,403)
            for method in ('post','put','patch','delete'):
                self.assertEqual(getattr(self.a,method)('/commerce/orders/test/refund-applications').status_code,403)
            read.assert_not_awaited()

    def test_other_object_never_fetches_its_details(self):
        self.admit(self.a)
        with patch.object(commerce,'_get',new_callable=AsyncMock,return_value={'data':{'orders':[{'order_id':'allowed'}]}}) as read:
            self.assertEqual(self.a.get('/commerce/orders/other').status_code,403)
            read.assert_awaited_once_with('/users/u1001/orders')

    def test_allowed_object_and_gateway_error(self):
        self.admit(self.a)
        with patch.object(commerce,'_get',new_callable=AsyncMock,side_effect=[{'data':{'orders':[{'order_id':'allowed'}]}},{'data':{'status':'demo'}}]):
            self.assertEqual(self.a.get('/commerce/orders/allowed/status').json()['data']['status'],'demo')
        with patch.object(commerce,'_get',new_callable=AsyncMock,side_effect=RuntimeError('private upstream detail')):
            response=self.a.get('/commerce/users/u1001/orders')
            self.assertEqual(response.status_code,502)
            self.assertNotIn('private upstream detail',response.text)

    def test_chat_actions_and_knowledge_cannot_bypass_scope(self):
        with patch.object(commerce,'_get',new_callable=AsyncMock,return_value={'data':{'orders':[]}}) as read:
            self.assertIsNone(asyncio.run(fetch_order('other')))
            read.assert_awaited_once_with('/users/u1001/orders')
        state=DialogueState(sender_id='test')
        state.focused_object=FocusedObject(id='other',type='product')
        with patch.object(commerce,'_get',new_callable=AsyncMock,return_value={'data':{'products':[]}}) as read:
            chunks=asyncio.run(ProductAPIProvider().retrieve(state))
            self.assertIn('演示列表',chunks[0].content)
            read.assert_awaited_once_with('/users/u1001/products')

    def test_avatar_owned_by_one_visitor_and_release_is_checked(self):
        self.admit(self.a); self.admit(self.b)
        self.assertEqual(self.a.get('/api/avatar/session').status_code,200)
        self.assertEqual(self.b.get('/api/avatar/session').status_code,409)
        self.assertEqual(self.b.delete('/api/avatar/session').status_code,403)
        self.assertEqual(self.b.post('/api/avatar/session/heartbeat').status_code,409)
        self.assertEqual(self.a.post('/api/avatar/session/heartbeat').status_code,200)
        self.create.assert_called_once()
        self.assertTrue(self.a.delete('/api/avatar/session').json()['released'])
        self.close.assert_called_once_with(['test-cloud-session'])
        self.assertEqual(self.b.get('/api/avatar/session').status_code,200)

    def test_expired_avatar_closed_before_transfer(self):
        self.admit(self.a); self.admit(self.b)
        self.a.get('/api/avatar/session')
        avatar._lease_deadline=time.monotonic()-1
        self.assertEqual(self.b.get('/api/avatar/session').status_code,200)
        self.close.assert_called_once_with(['test-cloud-session'])
        self.assertEqual(self.create.call_count,2)

    def test_failed_cloud_close_does_not_transfer_owner(self):
        owner=self.admit(self.a); self.admit(self.b)
        self.a.get('/api/avatar/session')
        avatar._lease_deadline=time.monotonic()-1
        self.close.side_effect=RuntimeError('private cloud detail')
        response=self.b.get('/api/avatar/session')
        self.assertEqual(response.status_code,502)
        self.assertNotIn('private cloud detail',response.text)
        self.assertEqual(avatar._session_owner,owner)
        self.create.assert_called_once()

    def test_parallel_avatar_acquisition_and_idle_cleanup(self):
        async def acquire():
            return await asyncio.gather(avatar.create_chat_session('a'),avatar.create_chat_session('b'),return_exceptions=True)
        results=asyncio.run(acquire())
        self.assertEqual(sum(isinstance(x,avatar.AvatarBusyError) for x in results),1)
        self.create.assert_called_once()
        avatar._lease_deadline=time.monotonic()-1
        asyncio.run(avatar.expire_chat_session())
        self.assertIsNone(avatar._session)
        self.close.assert_called_once()

    def test_missing_cloud_sdk_returns_clear_unavailable(self):
        self.admit(self.a)
        with patch.object(avatar,'LINGMOU_AVAILABLE',False):
            self.assertEqual(self.a.get('/api/avatar/session').status_code,503)
        self.create.assert_not_called()

    def test_shutdown_releases_cloud_session(self):
        self.admit(self.a)
        self.a.get('/api/avatar/session')
        asyncio.run(avatar.shutdown_chat_session())
        self.close.assert_called_once_with(['test-cloud-session'])
        self.assertIsNone(avatar._session)
        self.assertIsNone(avatar._session_owner)


class OpenDemoTests(unittest.TestCase):
    def test_no_access_cookie_or_password_file_needed(self):
        app = FastAPI()
        app.middleware('http')(protect_demo_api)
        app.include_router(access_router)
        app.include_router(visitor_router)
        with patch('construction_service.api.demo_access.DEMO_ACCESS_REQUIRED', False), \
             patch('construction_service.api.demo_access.access_password', side_effect=AssertionError('Password must not be read')), \
             patch('construction_service.api.visitor_session._signing_key', return_value=b'x' * 32), \
             TestClient(app) as client:
            self.assertTrue(client.get('/api/access/session').json()['authenticated'])
            self.assertEqual(client.get('/api/visitor/session').status_code, 200)
            self.assertNotIn(ACCESS_COOKIE, client.cookies)

    def test_open_entry_keeps_business_scope(self):
        app = FastAPI()
        app.middleware('http')(protect_demo_api)
        app.include_router(visitor_router)
        app.include_router(commerce_router)
        with patch('construction_service.api.demo_access.DEMO_ACCESS_REQUIRED', False), \
             patch('construction_service.api.visitor_session._signing_key', return_value=b'x' * 32), \
             TestClient(app) as client:
            self.assertEqual(client.get('/commerce/users/u1001/orders').status_code, 401)
            client.get('/api/visitor/session')
            self.assertEqual(client.get('/commerce/users/other/orders').status_code, 403)
            self.assertEqual(client.post('/commerce/orders/test/refund-applications').status_code, 403)


if __name__=='__main__': unittest.main()
