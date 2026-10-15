"""Generate Task 11 FastAPI evidence under evidence/step12/."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app.main import app
from app.memory import reset_all_sessions
from app.support_crew import ORDER_DEMO_RECORD_ID, POLICY_DEMO_QUERY

EVIDENCE_DIR = PROJECT_ROOT / "evidence" / "step12"


def _write(name: str, payload: object) -> None:
    path = EVIDENCE_DIR / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    reset_all_sessions()
    client = TestClient(app)

    policy = client.post("/ask", json={"query": POLICY_DEMO_QUERY, "session_id": "evidence-policy"})
    _write("http_ask_policy.json", {"request": {"query": POLICY_DEMO_QUERY}, "response": policy.json()})

    order_query = f"Check the status of order {ORDER_DEMO_RECORD_ID}."
    order = client.post("/ask", json={"query": order_query, "session_id": "evidence-order"})
    _write("http_ask_order.json", {"request": {"query": order_query}, "response": order.json()})

    order_status = client.post("/order-status", json={"record_id": ORDER_DEMO_RECORD_ID})
    _write("http_order_status.json", {"response": order_status.json()})

    ws_transcript: list[object] = []
    with client.websocket_connect("/ws/chat") as ws:
        ws_transcript.append(ws.receive_json())
        ws.send_text(json.dumps({"query": f"Check the status of order {ORDER_DEMO_RECORD_ID}."}))
        ws_transcript.append(ws.receive_json())
        ws.send_text(json.dumps({"query": "Is it likely to need escalation?"}))
        ws_transcript.append(ws.receive_json())
    _write("websocket_multiturn.json", {"transcript": ws_transcript})

    disconnect_demo: list[object] = []
    with client.websocket_connect("/ws/chat") as ws_a:
        disconnect_demo.append({"step": "client_a_connected", "payload": ws_a.receive_json()})
        ws_a.send_text(json.dumps({"query": POLICY_DEMO_QUERY}))
        disconnect_demo.append({"step": "client_a_response", "payload": ws_a.receive_json()})
    disconnect_demo.append({"step": "client_a_disconnected", "note": "context manager exit"})

    with client.websocket_connect("/ws/chat") as ws_b:
        disconnect_demo.append({"step": "client_b_connected", "payload": ws_b.receive_json()})
        ws_b.send_text(json.dumps({"query": POLICY_DEMO_QUERY}))
        disconnect_demo.append({"step": "client_b_response", "payload": ws_b.receive_json()})
    _write("websocket_disconnect_reconnect.json", {"steps": disconnect_demo})

    print(f"Wrote Task 11 evidence to {EVIDENCE_DIR}")


if __name__ == "__main__":
    main()
