import http.client
import json
import socket
import threading
import unittest
from unittest.mock import patch
from src.injection_prevention.local_tester import TesterHandler, TesterServer
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
    def test_oversized_request_rejection_never_runs_the_demo(self):
        with patch("src.injection_prevention.local_tester.run_demo") as demo:
            for _ in range(3):
                status, _, data = self.request(
                    'POST', '/api/test', 'A' * 65537, {'Content-Type': 'application/json'})
                self.assertEqual(status, 413)
                self.assertEqual(json.loads(data)['reason_code'], 'PAYLOAD_LIMIT')
            demo.assert_not_called()
        self.assertEqual(self.request('GET', '/api/samples')[0], 200)

    def test_oversized_headers_get_rejection_without_sending_the_body(self):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=2)
        try:
            connection.putrequest('POST', '/api/test')
            connection.putheader('Content-Type', 'application/json')
            connection.putheader('Content-Length', str(10 ** 12))
            connection.endheaders()
            response = connection.getresponse()
            self.assertEqual(response.status, 413)
            self.assertEqual(json.loads(response.read())['reason_code'], 'PAYLOAD_LIMIT')
        finally:
            connection.close()

    def test_stalled_rejected_body_does_not_hold_the_server(self):
        port = self.server.server_port
        with socket.create_connection(('127.0.0.1', port), timeout=2) as stalled:
            headers = (f'POST /api/test HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n'
                       'Content-Type: application/json\r\nContent-Length: 1000000000000\r\n\r\n')
            stalled.sendall(headers.encode('ascii'))
            response = http.client.HTTPResponse(stalled)
            response.begin()
            self.assertEqual(response.status, 413)
            response.read()
            # Keep the sender open without a body. The bounded drain must end
            # so the single-threaded server can serve another valid request.
            healthy = http.client.HTTPConnection('127.0.0.1', port, timeout=2)
            try:
                healthy.request('GET', '/api/samples')
                result = healthy.getresponse()
                self.assertEqual(result.status, 200)
                result.read()
            finally:
                healthy.close()

    def test_request_parse_error_without_headers_still_returns_safe_json(self):
        with patch.object(self.server, 'handle_error') as unexpected_error:
            with socket.create_connection(('127.0.0.1', self.server.server_port), timeout=2) as connection:
                connection.sendall(b'GET / HTTP/9.9\r\n\r\n')
                response = http.client.HTTPResponse(connection)
                response.begin()
                self.assertEqual(response.status, 505)
                self.assertEqual(json.loads(response.read())['state'], 'MANUAL_REVIEW')
            self.assertEqual(self.request('GET', '/api/samples')[0], 200)
            unexpected_error.assert_not_called()

    def test_early_parser_http09_default_still_frames_error_response(self):
        # CPython 3.13.5 and 3.14.6 can reject before assigning the parsed
        # version or headers. Reproduce that state on newer interpreters too.
        with patch.object(self.server, 'handle_error') as unexpected_error:
            for status in (400, 505):
                def reject_before_headers(handler, code=status):
                    handler.command = None
                    handler.requestline = 'synthetic malformed request'
                    handler.request_version = 'HTTP/0.9'
                    handler.close_connection = True
                    handler.send_error(code, 'synthetic raw detail')
                    return False
                with self.subTest(status=status), patch.object(TesterHandler, 'parse_request', reject_before_headers):
                    with socket.create_connection(('127.0.0.1', self.server.server_port), timeout=2) as connection:
                        connection.sendall(b'GET / HTTP/9.9\r\n\r\n')
                        response = http.client.HTTPResponse(connection)
                        response.begin()
                        self.assertEqual(response.status, status)
                        self.assertEqual(response.getheader('Content-Type'), 'application/json; charset=utf-8')
                        body = response.read()
                        self.assertEqual(int(response.getheader('Content-Length')), len(body))
                        self.assertEqual(json.loads(body), {'state': 'MANUAL_REVIEW', 'reason_code': 'HTTP_REQUEST_REJECTED'})
                        self.assertNotIn(b'synthetic raw detail', body)
            self.assertEqual(self.request('GET', '/api/samples')[0], 200)
            unexpected_error.assert_not_called()

    def test_other_rejected_post_bodies_never_run_the_demo(self):
        cases = (
            ('/api/test', {'Content-Type': 'text/plain'}, 415),
            ('/unknown', {'Content-Type': 'application/json'}, 404),
            ('/api/test', {'Content-Type': 'application/json', 'Origin': 'https://attacker.invalid'}, 403),
        )
        with patch("src.injection_prevention.local_tester.run_demo") as demo:
            for path, headers, expected_status in cases:
                status, _, data = self.request('POST', path, '{}', headers)
                self.assertEqual(status, expected_status)
                self.assertEqual(json.loads(data)['state'], 'MANUAL_REVIEW')
            demo.assert_not_called()
        self.assertEqual(self.request('GET', '/api/samples')[0], 200)

    def test_rate_limit_is_fail_closed_without_flooding(self):
        import time
        self.server.requests.extend([time.monotonic()]*120)
        status,_,data=self.request('GET','/api/samples')
        self.assertEqual(status,429);self.assertEqual(json.loads(data)['state'],'MANUAL_REVIEW')
