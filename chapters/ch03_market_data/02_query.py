"""03-2 실습: DuckDB로 저장된 분봉 질의하기

실행: python chapters/ch03_market_data/02_query.py
"""

from pathlib import Path

import pandas as pd

from marketdata import MinuteStore

pd.set_option("display.width", 120)
store = MinuteStore("data")

size_mb = sum(p.stat().st_size for p in store.base.rglob("*.parquet")) / 1024**2
print(f"저장 종목 {len(store.codes())}개, Parquet 합계 {size_mb:.1f} MB\n")

print("[1] 종목별·세션별 봉 수")
print(store.query("""
    SELECT stk_cd, session, count(*) AS bars, count(DISTINCT ts::DATE) AS days
    FROM bars GROUP BY ALL ORDER BY stk_cd, session
""").to_string(index=False))

print("\n[2] 정규장 분봉으로 만든 최근 3일 일봉 (005930)")
print(store.query("""
    SELECT ts::DATE AS date,
           first(open ORDER BY ts) AS open, max(high) AS high, min(low) AS low,
           last(close ORDER BY ts) AS close, sum(volume) AS volume
    FROM bars
    WHERE stk_cd = '005930' AND session IN ('regular', 'close')
    GROUP BY ALL ORDER BY date DESC LIMIT 3
""").to_string(index=False))

print("\n[3] 장 시작 30분(09:00~09:29) 거래대금 비중이 큰 날 (005930, 상위 3일)")
print(store.query("""
    SELECT ts::DATE AS date,
           round(100 * sum(close * volume) FILTER (WHERE strftime(ts, '%H:%M') < '09:30')
                 / sum(close * volume), 1) AS open30_pct
    FROM bars
    WHERE stk_cd = '005930' AND session IN ('regular', 'close')
    GROUP BY ALL ORDER BY open30_pct DESC LIMIT 3
""").to_string(index=False))

assert Path("data").exists()
