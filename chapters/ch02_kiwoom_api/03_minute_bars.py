"""02-5 실습 2: 분봉 조회 (ka10080) 와 DataFrame 변환

실행: python chapters/ch02_kiwoom_api/03_minute_bars.py 005930 1
"""

import sys

import pandas as pd

from kiwoom_api import KiwoomClient, to_price

stk_cd = sys.argv[1] if len(sys.argv) > 1 else "005930"
tic = sys.argv[2] if len(sys.argv) > 2 else "1"  # 1, 3, 5, 10, 15, 30, 45, 60분

client = KiwoomClient()
data, next_key = client.request(
    "ka10080",
    "/api/dostk/chart",
    {"stk_cd": stk_cd, "tic_scope": tic, "upd_stkpc_tp": "1"},  # 1: 수정주가 적용
)
rows = data["stk_min_pole_chart_qry"]
print(f"받은 봉 수: {len(rows)}  다음 페이지 있음: {bool(next_key)}")

df = pd.DataFrame(rows)
df["ts"] = pd.to_datetime(df["cntr_tm"], format="%Y%m%d%H%M%S")
for col, src in [("open", "open_pric"), ("high", "high_pric"), ("low", "low_pric"), ("close", "cur_prc")]:
    df[col] = df[src].map(to_price)
df["volume"] = df["trde_qty"].astype(int)
df = df[["ts", "open", "high", "low", "close", "volume"]].sort_values("ts").reset_index(drop=True)

last_day = df["ts"].dt.date.max()
day = df[df["ts"].dt.date == last_day]
hhmm = day["ts"].dt.strftime("%H:%M")
# 정규장: 09:00~15:19 연속매매 + 15:30 종가 단일가 봉 (15:20~15:29 동시호가 구간에는 봉이 없다)
regular = day[(hhmm >= "09:00") & (hhmm <= "15:30")]

print(f"\n{last_day} 봉 {len(day)}개 (시각 {day['ts'].min():%H:%M} ~ {day['ts'].max():%H:%M})")
print(f"그중 정규장(09:00~15:30) 봉 {len(regular)}개, 그 밖(NXT·시간외) {len(day) - len(regular)}개\n")
print(regular.head(5).to_string(index=False))
