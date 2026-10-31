"""03-4 실습: VWAP·상대거래량·상대강도 계산

실행: python chapters/ch03_market_data/04_indicators.py 005930 [YYYY-MM-DD]
"""

import sys

import pandas as pd

from marketdata import MinuteStore, add_relative_strength, add_relative_volume, add_vwap

stk_cd = sys.argv[1] if len(sys.argv) > 1 else "005930"
bench_cd = "069500"  # KODEX 200

store = MinuteStore("data")
df = add_relative_volume(store.load(stk_cd), lookback=20)
bench = store.load(bench_cd)

day_str = sys.argv[2] if len(sys.argv) > 2 else str(df["ts"].dt.date.max())
day = df[df["ts"].dt.date.astype(str) == day_str]
bench_day = bench[bench["ts"].dt.date.astype(str) == day_str]

d = add_vwap(day)
d = d.merge(add_relative_strength(day, bench_day)[["ts", "ret", "bench_ret", "rs"]], on="ts")

checkpoints = ["09:05", "09:30", "10:00", "11:00", "13:00", "15:19"]
view = d[d["ts"].dt.strftime("%H:%M").isin(checkpoints)]
print(f"{stk_cd} {day_str}  (기준: {bench_cd})\n")
print(pd.DataFrame({
    "시각": view["ts"].dt.strftime("%H:%M"),
    "종가": view["close"],
    "VWAP": view["vwap"].round(0).astype(int),
    "VWAP이격%": ((view["close"] / view["vwap"] - 1) * 100).round(2),
    "RVOL": view["rvol"].round(2),
    "종목수익%": view["ret"].round(2),
    "지수수익%": view["bench_ret"].round(2),
    "상대강도%p": view["rs"].round(2),
}).to_string(index=False))
