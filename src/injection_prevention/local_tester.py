"""Loopback-only synthetic test bench, not a production web server."""
import argparse
from collections import deque
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import time
from urllib.parse import urlsplit
from .boundary_contracts import ContractError, Limits, strict_json_loads
from .demo import SAMPLES, run_demo
from .qualification import qualification_report

ASSETS=Path(__file__).resolve().parents[2]/'web/local_tester'


class TesterServer(HTTPServer):
    def __init__(self,port=0):
        super().__init__(('127.0.0.1',port),TesterHandler)
        self.requests=deque(maxlen=121)


class TesterHandler(BaseHTTPRequestHandler):
    server_version='LocalInjectionTester'
    def setup(self):
        super().setup();self.connection.settimeout(3)

    def log_message(self,*args):
        pass  # No raw paths, request bodies or attack strings in ordinary logs.

    def send_content(self,status,body,kind='application/json; charset=utf-8'):
        self.send_response(status)
        self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers();self.wfile.write(body)

    def error_json(self,status,code):
        self.send_content(status,json.dumps({'state':'MANUAL_REVIEW','reason_code':code}).encode())

    def send_error(self,code,message=None,explain=None):
        self.error_json(code,'HTTP_REQUEST_REJECTED')

    def boundary_ok(self):
        expected=f'127.0.0.1:{self.server.server_port}'
        if self.headers.get_all('Host')!=[expected]:
            self.error_json(403,'INVALID_HOST');return False
        origins=self.headers.get_all('Origin',[])
        sites=self.headers.get_all('Sec-Fetch-Site',[])
        if len(origins)>1 or len(sites)>1 or (origins and origins[0]!='http://'+expected) or (sites and sites[0]=='cross-site'):
            self.error_json(403,'CROSS_ORIGIN_DENIED');return False
        now=time.monotonic()
        while self.server.requests and now-self.server.requests[0]>60:self.server.requests.popleft()
        if len(self.server.requests)>=120:
            self.error_json(429,'LOCAL_REQUEST_BUDGET');return False
        self.server.requests.append(now)
        return True

    def do_GET(self):
        if not self.boundary_ok():return
        try:
            path=urlsplit(self.path).path
            assets={'/':('index.html','text/html; charset=utf-8'),'/bench.js':('bench.js','text/javascript; charset=utf-8'),'/bench.css':('bench.css','text/css; charset=utf-8')}
            if path in assets:
                name,kind=assets[path]
                self.send_content(200,(ASSETS/name).read_bytes(),kind)
            elif path=='/api/samples':self.send_content(200,json.dumps(SAMPLES,ensure_ascii=True).encode())
            elif path=='/api/evaluation':self.send_content(200,json.dumps(qualification_report(),ensure_ascii=True).encode())
            else:self.error_json(404,'UNKNOWN_ROUTE')
        except (OSError,ValueError,TypeError,KeyError):
            self.error_json(503,'LOCAL_TEST_UNAVAILABLE')

    def do_POST(self):
        if not self.boundary_ok():return
        try:path=urlsplit(self.path).path
        except ValueError:self.error_json(400,'INVALID_REQUEST_TARGET');return
        if path!='/api/test':self.error_json(404,'UNKNOWN_ROUTE');return
        if self.headers.get('Transfer-Encoding') or len(self.headers.get_all('Content-Length',[]))!=1:
            self.error_json(400,'INVALID_BODY_LENGTH');return
        if self.headers.get('Content-Type','').split(';')[0].strip().lower()!='application/json':
            self.error_json(415,'JSON_REQUIRED');return
        try:length=int(self.headers['Content-Length'])
        except (ValueError,TypeError):self.error_json(400,'INVALID_BODY_LENGTH');return
        if not 0<length<=Limits().max_bytes:self.error_json(413,'PAYLOAD_LIMIT');return
        try:
            raw=self.rfile.read(length)
            if len(raw)!=length:raise ContractError('INCOMPLETE_BODY')
            result=run_demo(strict_json_loads(raw))
            self.send_content(200,json.dumps(result,ensure_ascii=True,allow_nan=False).encode())
        except ContractError as error:self.error_json(400,str(error))
        except (ValueError,TypeError,TimeoutError):self.error_json(400,'INVALID_TEST_INPUT')
        except Exception:self.error_json(500,'LOCAL_TEST_UNAVAILABLE')

    def unsupported(self):self.error_json(405,'METHOD_NOT_ALLOWED')
    do_OPTIONS=unsupported
    do_PUT=unsupported
    do_DELETE=unsupported
    do_PATCH=unsupported
    do_HEAD=unsupported
    do_TRACE=unsupported
    do_CONNECT=unsupported


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    if not 0<=args.port<=65535:parser.error('Use a local port from 0 to 65535.')
    server=TesterServer(args.port)
    print(f'Local synthetic tester: http://127.0.0.1:{server.server_port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()


if __name__=='__main__':main()
