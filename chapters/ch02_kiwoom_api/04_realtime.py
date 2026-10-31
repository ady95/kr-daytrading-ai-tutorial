"""02-5 실습 3: WebSocket 실시간 체결 수신 (0B)

장중에 실행해야 데이터가 들어옵니다.
실행: python chapters/ch02_kiwoom_api/04_realtime.py 005930 30
"""

import asyncio
import sys

from kiwoom_api import TICK_FIELDS, KiwoomClient, KiwoomWebSocket, to_price

stk_cd = sys.argv[1] if len(sys.argv) > 1 else "005930"
seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 30

client = KiwoomClient()
count = 0


def on_real(d: dict) -> None:
    global count
    count += 1
    v = d["values"]
    side = "매수" if v.get("15", "").startswith("+") else "매도"
    print(
        f"{v.get('20')}  {d['item']}  현재가 {to_price(v.get('10', '')):>8,}"
        f"  체결량 {abs(int(v.get('15', '0') or 0)):>6,} ({side})"
        f"  누적 {int(v.get('13', '0') or 0):>12,}"
    )


ws = KiwoomWebSocket(client.token, client.env)
print(f"{stk_cd} 실시간 체결을 {seconds}초 동안 받습니다. (항목: {', '.join(TICK_FIELDS.values())})")
asyncio.run(ws.run(items=[stk_cd], types=["0B"], on_real=on_real, seconds=seconds))
print(f"수신한 체결 메시지: {count}건")
