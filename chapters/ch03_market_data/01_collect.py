"""03-1 실습: 1분봉 수집 (처음 실행은 보관 범위 전체, 다시 실행하면 증분)

실행: python chapters/ch03_market_data/01_collect.py [종목코드 ...]
"""

import sys
import time

from kiwoom_api import KiwoomClient
from marketdata import MinuteStore, update

# 삼성전자, SK하이닉스, KODEX 200(시장 기준), KODEX 코스닥150(코스닥 기준)
codes = sys.argv[1:] or ["005930", "000660", "069500", "229200"]

client = KiwoomClient()
store = MinuteStore("data")

total_start = time.perf_counter()
for stk_cd in codes:
    t0 = time.perf_counter()
    added, last = update(client, store, stk_cd)
    df = store.load(stk_cd)
    print(
        f"{stk_cd}: 새 봉 {added:>7,}개 / 저장 {len(df):>7,}개"
        f"  ({df['ts'].min():%Y-%m-%d} ~ {last:%Y-%m-%d %H:%M})  {time.perf_counter() - t0:5.1f}초"
    )
print(f"전체 {time.perf_counter() - total_start:.1f}초, API 재시도 {client.retry_count}회")
