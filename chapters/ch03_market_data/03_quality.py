"""03-3 실습: 분봉 품질 검사와 일봉(ka10081) 대조

실행: python chapters/ch03_market_data/03_quality.py
"""

import pandas as pd

from kiwoom_api import KiwoomClient, to_price
from marketdata import MinuteStore, check_all, daily_from_minute, fill_regular

store = MinuteStore("data")

print("[1] 종목별 품질 요약")
reports = {}
for stk_cd in store.codes():
    q = check_all(store.load(stk_cd))
    reports[stk_cd] = q
    short = q[q["missing"] > 0]
    print(
        f"{stk_cd}: {len(q)}일, 평균 {q['bars'].mean():.1f}봉/일, 누락 있는 날 {len(short)}일,"
        f" 종가봉 없는 날 {(~q['has_close_bar']).sum()}일, OHLC 모순 {q['bad_ohlc'].sum()}건, 중복 {q['dup_ts'].sum()}건"
    )

print("\n[2] 20분 이상 연속으로 비어 있는 구간 (모든 종목에서 겹치면 시장 전체 중단)")
gaps = pd.concat(
    [q.assign(stk_cd=cd)[["date", "stk_cd", "long_gaps"]] for cd, q in reports.items()]
).explode("long_gaps").dropna()
gaps["start"] = gaps["long_gaps"].str[0]
gaps["minutes"] = gaps["long_gaps"].str[1]
summary = gaps.groupby(["date", "start", "minutes"])["stk_cd"].apply(list).reset_index()
print(summary.to_string(index=False))

print("\n[3] 분봉으로 만든 일봉 vs ka10081 일봉 (005930, 최근 3일)")
client = KiwoomClient()
mine = daily_from_minute(store.load("005930"))[["close", "volume"]]
base_dt = mine.index.max().strftime("%Y%m%d")
data, _ = client.request("ka10081", "/api/dostk/chart", {"stk_cd": "005930", "base_dt": base_dt, "upd_stkpc_tp": "1"})
api = pd.DataFrame(data["stk_dt_pole_chart_qry"]).head(3)
api = pd.DataFrame({
    "date": pd.to_datetime(api["dt"]).dt.date,
    "api_close": api["cur_prc"].map(to_price),
    "api_volume": api["trde_qty"].astype(int),
}).set_index("date")
print(api.join(mine.rename(columns={"close": "my_close", "volume": "my_volume"})).to_string())

print("\n[4] 거래가 없는 분 채우기 (000660)")
df = store.load("000660")
q = reports["000660"]
for date in [d for d, g in zip(q["date"], q["long_gaps"]) if g][:1] + [d for d, g, m in zip(q["date"], q["long_gaps"], q["missing"]) if m and not g][:1]:
    day = df[df["ts"].dt.date == date]
    filled = fill_regular(day)
    n = (day["session"] == "regular").sum()
    print(f"{date}: 연속매매 봉 {n}개 -> 채운 뒤 {len(filled)}개 (채운 분 {len(filled) - n}개, 남긴 공백 {380 - len(filled)}분)")
