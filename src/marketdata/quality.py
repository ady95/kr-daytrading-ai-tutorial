"""분봉 품질 검사: 누락 봉, 시장 전체 매매 중단, OHLC 모순, 중복 시각

키움 분봉은 체결이 없는 분에는 봉을 만들지 않습니다(거래량 0 봉이 없음).
그래서 '누락'은 데이터 오류일 수도, 거래가 없었던 것일 수도, 시장이 멈춘 것일 수도 있습니다.
"""

from __future__ import annotations

import pandas as pd

from .normalize import session_times

HALT_MINUTES = 20  # 연속으로 이만큼 비면 매매 중단(서킷브레이커 등) 후보로 본다


def regular_minutes(date) -> list[str]:
    """그날 연속매매 구간의 분 목록 (평소 09:00~15:19, 380분)"""
    start, cont_end, _ = session_times(date)
    day = pd.Timestamp(str(date))
    rng = pd.date_range(day + pd.Timedelta(f"{start[:2]}h{start[3:]}min"),
                        day + pd.Timedelta(f"{cont_end[:2]}h{cont_end[3:]}min"), freq="min", inclusive="left")
    return list(rng.strftime("%H:%M"))


EXPECTED_BARS = len(regular_minutes("2026-10-30")) + 1  # 평소: 380 + 종가 1


def _runs(missing: list[str], minutes: list[str]) -> list[tuple[str, int]]:
    """누락된 분을 연속 구간(시작 시각, 길이)으로 묶는다."""
    idx = {m: i for i, m in enumerate(minutes)}
    runs: list[tuple[str, int]] = []
    for m in missing:
        if runs and idx[m] == idx[runs[-1][0]] + runs[-1][1]:
            runs[-1] = (runs[-1][0], runs[-1][1] + 1)
        else:
            runs.append((m, 1))
    return runs


def check_day(day: pd.DataFrame) -> dict:
    """하루치 분봉(한 종목)을 검사합니다."""
    date = day["ts"].dt.date.iloc[0]
    minutes = regular_minutes(date)
    reg = day[day["session"] == "regular"]
    have = set(reg["ts"].dt.strftime("%H:%M"))
    missing = [m for m in minutes if m not in have]
    runs = _runs(missing, minutes)
    both = day[day["session"].isin(["regular", "close"])]
    bad_ohlc = both[
        (both["low"] > both[["open", "close"]].min(axis=1)) | (both["high"] < both[["open", "close"]].max(axis=1))
    ]
    return {
        "date": date,
        "bars": len(reg) + int((day["session"] == "close").any()),
        "expected": len(minutes) + 1,
        "missing": len(missing),
        "long_gaps": [r for r in runs if r[1] >= HALT_MINUTES],
        "has_close_bar": (day["session"] == "close").any(),
        "bad_ohlc": len(bad_ohlc),
        "dup_ts": int(day["ts"].duplicated().sum()),
    }


def check_all(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame([check_day(g) for _, g in df.groupby(df["ts"].dt.date)])


def fill_regular(day: pd.DataFrame, max_gap: int = HALT_MINUTES - 1) -> pd.DataFrame:
    """거래가 없어 빠진 연속매매 분을 직전 종가·거래량 0으로 채운 하루치 분봉을 만듭니다.

    max_gap분보다 긴 공백(서킷브레이커 등 매매 중단)은 채우지 않고 비워 둡니다.
    멈춘 시장을 직전 가격으로 채우면 백테스트가 체결할 수 없던 시각에 체결해 버립니다.
    """
    reg = day[day["session"] == "regular"].set_index("ts")
    if reg.empty:
        return reg.reset_index()
    date = reg.index[0].normalize()
    full = pd.DatetimeIndex(
        [date + pd.Timedelta(f"{m[:2]}h{m[3:]}min") for m in regular_minutes(date.date())], name="ts"
    )
    out = reg.reindex(full)
    gap = out["close"].isna()
    run_id = (gap != gap.shift()).cumsum()
    run_len = gap.groupby(run_id).transform("sum")
    fillable = gap & (run_len <= max_gap)
    out["close"] = out["close"].ffill().where(~gap | fillable)
    for col in ["open", "high", "low"]:
        out[col] = out[col].fillna(out["close"])
    out["volume"] = out["volume"].fillna(0).astype("int64")
    out["session"] = "regular"
    # 채우지 않은 분(매매 중단, 장 시작 직후 첫 체결 전)은 버린다
    return out.dropna(subset=["close"]).reset_index()
