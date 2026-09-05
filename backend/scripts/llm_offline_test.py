import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.llm_client import LLMClient


class FakeOpenAI(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        content = (
            '```json\n{"debates": [{"topic": "为何选故宫", '
            '"plan_side": {"role": "规划方", "point": "匹配偏好"}, '
            '"traveler_side": {"role": "游客方", "point": "想要备选"}, '
            '"verdict": {"decision": "主推故宫", "reason": "确定性最高"}}]}\n```'
        )
        resp = {"choices": [{"message": {"role": "assistant", "content": content}}]}
        data = json.dumps(resp).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


server = HTTPServer(("127.0.0.1", 0), FakeOpenAI)
port = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()

os.environ["LLM_MODE"] = "real"
os.environ["LLM_API_KEY"] = "test-key"
os.environ["LLM_BASE_URL"] = f"http://127.0.0.1:{port}/v1"
os.environ["LLM_TIMEOUT_SECONDS"] = "5"
os.environ["LLM_MAX_RETRIES"] = "0"

client = LLMClient()
result = client.try_generate_json("生成辩论")
assert result and result["debates"][0]["topic"] == "为何选故宫", result
print("real-mode parse ok:", result["debates"][0]["topic"])

os.environ["LLM_BASE_URL"] = "http://127.0.0.1:9/v1"
fallback_client = LLMClient()
os.environ["LLM_MAX_RETRIES"] = "2"
t0 = time.time()
fallback = fallback_client.try_generate_json("生成辩论")
elapsed = time.time() - t0
assert fallback is None, fallback
print(f"failure fallback ok: returns None after {elapsed:.1f}s")

server.shutdown()
print("LLM OFFLINE TESTS PASSED")
