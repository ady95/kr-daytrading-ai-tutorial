"""키움 분봉 응답(ka10080)을 분석용 표 형식으로 정규화합니다.

정규화 결과 컬럼: ts, stk_cd, open, high, low, close, volume, session
- ts: 봉 시작 시각(한국시간, timezone 없음). 09:00 봉 = 09:00:00~09:00:59 체결
- session: pre(개장 전) / regular(연속매매) / close(종가 단일가) / after(그 이후)
"""

from __future__ import annotations

import pandas as pd

from kiwoom_api import to_price

COLUMNS = ["ts", "stk_cd", "open", "high", "low", "close", "volume", "session"]

# (개장, 연속매매 종료, 종가 단일가 체결) — 평소 일정
DEFAULT_SESSION = ("09:00", "15:20", "15:30")

# 개장·폐장 시각이 바뀌는 날. 해마다 거래소 공지를 보고 추가합니다.
SPECIAL_SESSIONS = {
    "2025-11-13": ("10:00", "16:20", "16:30"),  # 대학수학능력시험일: 1시간 늦게 열고 늦게 닫음
    "2026-01-02": ("10:00", "15:20", "15:30"),  # 새해 첫 거래일: 1시간 늦게 개장
}

# 종가 단일가가 연장되면 종가 봉이 15:30이 아니라 15:32 등에 찍힌다 (실측)
CLOSE_WINDOW_MIN = 5


def session_times(date) -> tuple[str, str, str]:
    return SPECIAL_SESSIONS.get(str(date), DEFAULT_SESSION)


def _to_min(hhmm: str) -> int:
    return int(hhmm[:2]) * 60 + int(hhmm[3:])


def label_session(ts: pd.Series) -> pd.Series:
    hhmm = ts.dt.hour * 60 + ts.dt.minute  # 자정부터 몇 분째인지 (문자열 비교보다 빠르다)
    # 날짜마다 그날의 일정(평소 또는 SPECIAL_SESSIONS)을 붙인다
    day = ts.dt.normalize()
    sched = {d: [_to_min(t) for t in session_times(d.date())] for d in day.unique()}
    start = day.map({d: s[0] for d, s in sched.items()})
    cont_end = day.map({d: s[1] for d, s in sched.items()})
    close = day.map({d: s[2] for d, s in sched.items()})
    close_end = close + CLOSE_WINDOW_MIN

    session = pd.Series("after", index=ts.index)
    session[hhmm < start] = "pre"
    session[(hhmm >= start) & (hhmm < cont_end)] = "regular"
    session[(hhmm >= close) & (hhmm < close_end)] = "close"
    return session


def normalize_minute(rows: list[dict], stk_cd: str) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=COLUMNS)
    raw = pd.DataFrame(rows)
    df = pd.DataFrame({
        "ts": pd.to_datetime(raw["cntr_tm"], format="%Y%m%d%H%M%S"),
        "stk_cd": stk_cd,
        "open": raw["open_pric"].map(to_price),
        "high": raw["high_pric"].map(to_price),
        "low": raw["low_pric"].map(to_price),
        "close": raw["cur_prc"].map(to_price),
        "volume": raw["trde_qty"].astype("int64"),
    })
    df = df.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    df["session"] = label_session(df["ts"])
    return df[COLUMNS]
