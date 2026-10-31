"""키움증권 WebSocket 실시간 시세 클라이언트

접속 → LOGIN(접근토큰) → REG(실시간 항목 등록) → 수신 루프.
서버가 보내는 PING은 같은 메시지를 그대로 돌려보내야 연결이 유지됩니다.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable

import websockets

WS_HOSTS = {
    "paper": "wss://mockapi.kiwoom.com:10000",
    "real": "wss://api.kiwoom.com:10000",
}
WS_PATH = "/api/dostk/websocket"

# 실시간 타입 (공식 문서 기준)
REAL_TYPES = {
    "00": "주문체결",
    "04": "잔고",
    "0B": "주식체결",
    "0D": "주식호가잔량",
}

# 0B(주식체결) values의 주요 항목 코드 (공식 문서 기준)
TICK_FIELDS = {
    "20": "체결시간",
    "10": "현재가",
    "11": "전일대비",
    "12": "등락율",
    "15": "거래량",  # +는 매수 체결, -는 매도 체결
    "13": "누적거래량",
    "14": "누적거래대금",
    "27": "최우선매도호가",
    "28": "최우선매수호가",
}

OnReal = Callable[[dict], Awaitable[None] | None]


class KiwoomWebSocket:
    def __init__(self, token: str, env: str = "paper"):
        self.url = WS_HOSTS[env] + WS_PATH
        self.token = token

    async def run(self, items: list[str], types: list[str], on_real: OnReal, seconds: float | None = None) -> None:
        async with websockets.connect(self.url) as ws:
            await ws.send(json.dumps({"trnm": "LOGIN", "token": self.token}))
            login = json.loads(await ws.recv())
            if login.get("return_code") != 0:
                raise RuntimeError(f"LOGIN 실패: {login}")

            await ws.send(json.dumps({
                "trnm": "REG",
                "grp_no": "1",
                "refresh": "1",  # 1: 기존 등록 유지하고 추가
                "data": [{"item": items, "type": types}],
            }))

            loop = asyncio.get_running_loop()
            end = loop.time() + seconds if seconds else None
            while end is None or loop.time() < end:
                timeout = None if end is None else max(0.1, end - loop.time())
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
                except asyncio.TimeoutError:
                    break
                msg = json.loads(raw)
                trnm = msg.get("trnm")
                if trnm == "PING":
                    await ws.send(raw)
                elif trnm == "REAL":
                    for d in msg.get("data", []):
                        result = on_real(d)
                        if asyncio.iscoroutine(result):
                            await result
                elif trnm == "REG" and msg.get("return_code") != 0:
                    raise RuntimeError(f"REG 실패: {msg}")
