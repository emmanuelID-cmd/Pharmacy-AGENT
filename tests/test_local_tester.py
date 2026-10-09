import http.client
import json
import threading
import unittest
from src.injection_prevention.local_tester import TesterServer
from src.injection_prevention.demo import SAMPLES


class LocalTesterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=TesterServer()
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=5)
    def setUp(self):self.server.requests.clear()
    def request(self,method,path,body=None,headers=None):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        c.request(method,path,body=body,headers=headers or {})
        r=c.getresponse();status=r.status;h=dict(r.getheaders());data=r.read();c.close()
        return status,h,data
    def test_assets_and_security_headers(self):
        for path in ('/','/bench.js','/bench.css'):
            status,headers,data=self.request('GET',path)
            self.assertEqual(status,200);self.assertTrue(data)
            self.assertIn("script-src 'self'",headers['Content-Security-Policy'])
            self.assertEqual(headers['X-Content-Type-Options'],'nosniff')
        _,_,js=self.request('GET','/bench.js')
        self.assertNotIn(b'innerHTML',js);self.assertNotIn(b'eval(',js)
        self.assertIn(b'textContent',js)
    def test_real_api_and_safe_error_routes(self):
        base={k:v for k,v in SAMPLES[1].items() if k not in {'id','name'}}
        status,_,data=self.request('POST','/api/test',json.dumps(base),{'Content-Type':'application/json'})
        self.assertEqual(status,200);self.assertEqual(json.loads(data)['detector']['decision'],'REJECT')
        for path in ('/api/samples','/api/evaluation'):
            self.assertEqual(self.request('GET',path)[0],200)
        for method,path in (('GET','/../../.env'),('POST','/unknown'),('PUT','/api/test'),('OPTIONS','/api/test')):
            status,_,data=self.request(method,path)
            self.assertIn(status,(404,405));self.assertEqual(json.loads(data)['state'],'MANUAL_REVIEW')
    def test_invalid_origin_host_payloads_and_json(self):
        self.assertEqual(self.request('GET','/',headers={'Host':'attacker.invalid'})[0],403)
        self.assertEqual(self.request('GET','/',headers={'Origin':'https://attacker.invalid'})[0],403)
        for raw in ('{','{"source":"inventory","source":"fda"}','{"value":NaN}'):
            status,_,data=self.request('POST','/api/test',raw,{'Content-Type':'application/json'})
            self.assertEqual(status,400);self.assertNotIn(b'value',data);self.assertNotIn(b'source',data)
        self.assertEqual(self.request('POST','/api/test','{}',{'Content-Type':'text/plain'})[0],415)
        self.assertEqual(self.request('POST','/api/test','A'*65537,{'Content-Type':'application/json'})[0],413)
    def test_rate_limit_is_fail_closed_without_flooding(self):
        import time
        self.server.requests.extend([time.monotonic()]*120)
        status,_,data=self.request('GET','/api/samples')
        self.assertEqual(status,429);self.assertEqual(json.loads(data)['state'],'MANUAL_REVIEW')
