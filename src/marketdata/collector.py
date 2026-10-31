"""분봉 수집기: 처음에는 보관 범위 끝까지, 이후에는 저장된 마지막 봉 이후만 받습니다."""

from __future__ import annotations

import time

import pandas as pd

from kiwoom_api import KiwoomClient

from .normalize import normalize_minute
from .store import MinuteStore

LIST_KEY = "stk_min_pole_chart_qry"


def fetch_minute(
    client: KiwoomClient,
    stk_cd: str,
    tic: int = 1,
    since: pd.Timestamp | None = None,
    interval: float = 0.3,
) -> pd.DataFrame:
    """최신 봉부터 과거로 연속조회합니다. since가 있으면 그 시각 이전 봉이 나오는 페이지에서 멈춥니다."""
    body = {"stk_cd": stk_cd, "tic_scope": str(tic), "upd_stkpc_tp": "1"}  # 수정주가 적용
    rows: list[dict] = []
    next_key = ""
    while True:
        data, next_key = client.request("ka10080", "/api/dostk/chart", body, next_key)
        page = data.get(LIST_KEY, [])
        rows += page
        if not next_key or not page:
            break
        oldest = pd.to_datetime(page[-1]["cntr_tm"], format="%Y%m%d%H%M%S")
        if since is not None and oldest <= since:
            break
        time.sleep(interval)
    df = normalize_minute(rows, stk_cd)
    return df if since is None else df[df["ts"] > since]


def update(client: KiwoomClient, store: MinuteStore, stk_cd: str, tic: int = 1) -> tuple[int, pd.Timestamp | None]:
    """한 종목의 저장소를 최신으로 갱신합니다. (새 봉 수, 갱신 후 마지막 시각)을 돌려줍니다."""
    since = store.last_ts(stk_cd)
    # 마지막 날은 장중에 저장됐을 수 있으므로 그날 0시부터 다시 받아 덮어쓴다
    if since is not None:
        since = since.normalize() - pd.Timedelta(seconds=1)
    new = fetch_minute(client, stk_cd, tic, since)
    added = store.save(stk_cd, new) if not new.empty else 0
    return added, store.last_ts(stk_cd)
