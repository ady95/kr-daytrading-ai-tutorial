"""정규장 분봉으로 계산하는 기본 지표: 일봉, VWAP, 상대거래량, 상대강도"""

from __future__ import annotations

import pandas as pd


def regular_only(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["session"].isin(["regular", "close"])]


def daily_from_minute(df: pd.DataFrame) -> pd.DataFrame:
    """정규장 분봉으로 일봉을 만듭니다. 종가는 15:30 종가 단일가 봉(=다음 날 기준가)입니다."""
    reg = regular_only(df)
    g = reg.groupby(reg["ts"].dt.date)
    out = pd.DataFrame({
        "open": g["open"].first(),
        "high": g["high"].max(),
        "low": g["low"].min(),
        "close": g["close"].last(),
        "volume": g["volume"].sum(),
        "value": g.apply(lambda d: (d["close"] * d["volume"]).sum(), include_groups=False),
    })
    out.index.name = "date"
    return out


def add_vwap(day: pd.DataFrame) -> pd.DataFrame:
    """하루치(한 종목) 정규장 분봉에 당일 누적 VWAP을 더합니다. 매일 09:00에 새로 시작합니다."""
    d = regular_only(day).copy()
    typical = (d["high"] + d["low"] + d["close"]) / 3
    d["vwap"] = (typical * d["volume"]).cumsum() / d["volume"].cumsum()
    return d


def add_relative_volume(df: pd.DataFrame, lookback: int = 20) -> pd.DataFrame:
    """상대거래량(RVOL): 오늘 이 시각까지의 누적거래량 / 지난 lookback일 같은 시각 누적거래량 평균.

    지난 날들의 값만 쓰므로(shift) 장중 그 시각에 실제로 계산할 수 있는 값입니다.
    """
    d = regular_only(df)[["ts", "volume"]].copy()
    d["date"] = d["ts"].dt.date
    d["hhmm"] = d["ts"].dt.strftime("%H:%M")
    # 체결 없는 분은 봉이 없으므로 날짜×분 격자로 펼친 뒤 누적한다
    grid = d.pivot_table(index="date", columns="hhmm", values="volume", aggfunc="sum").fillna(0).cumsum(axis=1)
    base = grid.shift(1).rolling(lookback, min_periods=lookback).mean()
    rvol = (grid / base).stack().rename("rvol").reset_index()
    out = df.copy()
    out["date"] = out["ts"].dt.date
    out["hhmm"] = out["ts"].dt.strftime("%H:%M")
    return out.merge(rvol, on=["date", "hhmm"], how="left").drop(columns=["date", "hhmm"])


def add_relative_strength(day: pd.DataFrame, bench_day: pd.DataFrame) -> pd.DataFrame:
    """상대강도: (종목의 시가 대비 수익률) - (기준 지수 ETF의 시가 대비 수익률), 단위 %p."""
    d = regular_only(day).copy()
    b = regular_only(bench_day)[["ts", "close"]].rename(columns={"close": "bench"})
    d = pd.merge_asof(d.sort_values("ts"), b.sort_values("ts"), on="ts")  # 같은 시각 또는 직전 봉
    d["ret"] = (d["close"] / d["open"].iloc[0] - 1) * 100
    d["bench_ret"] = (d["bench"] / b["bench"].iloc[0] - 1) * 100
    d["rs"] = d["ret"] - d["bench_ret"]
    return d
