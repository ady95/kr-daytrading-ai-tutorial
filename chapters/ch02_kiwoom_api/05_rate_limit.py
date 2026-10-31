"""02-6 실습: 유량 제한 관찰과 자동 재시도

1) 쉬지 않고 연속 호출해 HTTP 429가 언제 나는지 봅니다.
2) KiwoomClient.request_all()로 같은 작업을 하면 재시도로 누락 없이 끝나는지 확인합니다.

실행: python chapters/ch02_kiwoom_api/05_rate_limit.py
"""

import time

import requests

from kiwoom_api import KiwoomClient

client = KiwoomClient()
body = {"stk_cd": "005930", "tic_scope": "1", "upd_stkpc_tp": "1"}

# 1) 재시도 없이 20번 연달아 호출
headers = {
    "Content-Type": "application/json;charset=UTF-8",
    "authorization": f"Bearer {client.token}",
    "api-id": "ka10080",
}
codes = []
t0 = time.perf_counter()
for _ in range(20):
    r = requests.post(f"{client.host}/api/dostk/chart", headers=headers, json=body, timeout=10)
    codes.append(r.status_code)
elapsed = time.perf_counter() - t0
blocked = codes.count(429)
print(f"[재시도 없음] 20회 / {elapsed:.1f}초 -> 성공 {codes.count(200)}회, 429 {blocked}회")
if blocked:
    print(f"  429 응답 예: {r.json() if r.status_code == 429 else '(마지막 응답은 성공)'}")

time.sleep(2)

# 2) 재시도가 들어간 request_all로 10페이지
t0 = time.perf_counter()
rows = client.request_all("ka10080", "/api/dostk/chart", body, "stk_min_pole_chart_qry", max_pages=10, interval=0.0)
elapsed = time.perf_counter() - t0
print(f"[자동 재시도] 10페이지 {len(rows):,}봉 / {elapsed:.1f}초, 재시도 {client.retry_count}회")
print(f"  범위: {rows[-1]['cntr_tm']} ~ {rows[0]['cntr_tm']}")
