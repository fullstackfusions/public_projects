# /// script
# requires-python = ">=3.11"
# dependencies = ["boto3>=1.35"]
# ///
"""Local stand-in for CloudFront's /api/* behaviour, for `npm run dev`.

Forwards GET /api/* to the API function URL, signed with SigV4 (like OAC) and with
`x-chaperone-view: public` (like the origin custom header), so the dev server sees exactly
what the live site will: masked answers.

    CHAPERONE_API_URL=https://<id>.lambda-url.us-east-1.on.aws AWS_PROFILE=chaperone-agent \
        uv run --script dev_proxy.py          # listens on 127.0.0.1:8787

    --local   run the API handler in this process instead (code not deployed yet). Needs
              TABLE_NAME and ACCOUNT_ID; reads DynamoDB with your credentials. Table reads
              are data events (not in the trail), but /api/review's existence checks are
              management events and will show up in your own session.
"""

import os
import sys
import urllib.parse
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

LOCAL = "--local" in sys.argv
API_URL = os.environ.get("CHAPERONE_API_URL", "").rstrip("/")
REGION = os.environ.get("AWS_REGION", "us-east-1")
session = boto3.Session()


class Proxy(BaseHTTPRequestHandler):
    def do_GET(self):
        if not self.path.startswith("/api/"):
            self.send_error(404)
            return
        if LOCAL:
            return self._local()
        req = AWSRequest(method="GET", url=API_URL + self.path, headers={"x-chaperone-view": "public"})
        SigV4Auth(session.get_credentials().get_frozen_credentials(), "lambda", REGION).add_auth(req)
        try:
            with urllib.request.urlopen(urllib.request.Request(req.url, headers=dict(req.headers)), timeout=60) as r:
                status, body, ctype = r.status, r.read(), r.headers.get("content-type", "application/json")
        except urllib.error.HTTPError as e:
            status, body, ctype = e.code, e.read(), e.headers.get("content-type", "application/json")
        self.send_response(status)
        self.send_header("content-type", ctype)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _local(self):
        from handlers import api
        path, _, query = self.path.partition("?")
        r = api.handler({"rawPath": path, "queryStringParameters": dict(urllib.parse.parse_qsl(query)),
                         "headers": {"x-chaperone-view": "public"}}, None)
        body = r["body"].encode()
        self.send_response(r["statusCode"])
        for k, v in r["headers"].items():
            self.send_header(k, v)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    if LOCAL:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
    print("dev proxy on http://127.0.0.1:8787 ->", "local handler" if LOCAL else API_URL)
    ThreadingHTTPServer(("127.0.0.1", 8787), Proxy).serve_forever()
