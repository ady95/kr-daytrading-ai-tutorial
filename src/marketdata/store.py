"""분봉 저장소: 종목별 Parquet 파일 + DuckDB 질의

data/minute_1m/stk_cd=005930/bars.parquet
data/minute_1m/stk_cd=000660/bars.parquet
...
폴더 이름의 `stk_cd=` 형식(하이브 파티션) 덕분에 DuckDB가 종목코드를 컬럼으로 읽습니다.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from .normalize import CLOSE_WINDOW_MIN, DEFAULT_SESSION, SPECIAL_SESSIONS, label_session


class MinuteStore:
    def __init__(self, root: str | Path = "data", tic: int = 1):
        self.base = Path(root) / f"minute_{tic}m"

    def path(self, stk_cd: str) -> Path:
        return self.base / f"stk_cd={stk_cd}" / "bars.parquet"

    def _read(self, stk_cd: str, columns: list[str] | None = None) -> pd.DataFrame | None:
        p = self.path(stk_cd)
        return pd.read_parquet(p, columns=columns) if p.exists() else None

    def load(self, stk_cd: str) -> pd.DataFrame | None:
        """session은 저장하지 않고 읽을 때 계산합니다. 장 운영 캘린더를 고치면 과거 데이터에도 바로 반영됩니다."""
        df = self._read(stk_cd)
        if df is None:
            return None
        df.insert(1, "stk_cd", stk_cd)
        df["session"] = label_session(df["ts"])
        return df

    def last_ts(self, stk_cd: str) -> pd.Timestamp | None:
        df = self._read(stk_cd, columns=["ts"])
        return None if df is None or df.empty else df["ts"].max()

    def save(self, stk_cd: str, new: pd.DataFrame) -> int:
        """기존 파일과 합쳐 저장하고, 새로 늘어난 봉 수를 돌려줍니다. 같은 시각의 봉은 새 값으로 덮어씁니다."""
        old = self._read(stk_cd)
        before = 0 if old is None else len(old)
        merged = new if old is None else pd.concat([old, new])
        merged = merged.drop_duplicates("ts", keep="last").sort_values("ts").reset_index(drop=True)
        # stk_cd는 폴더 이름에 들어 있으므로 파일에서는 뺀다 (DuckDB가 파티션 컬럼으로 복원)
        p = self.path(stk_cd)
        p.parent.mkdir(parents=True, exist_ok=True)
        merged.drop(columns=["stk_cd", "session"], errors="ignore").to_parquet(p, index=False)
        return len(merged) - before

    def codes(self) -> list[str]:
        return sorted(p.name.split("=", 1)[1] for p in self.base.glob("stk_cd=*"))

    def query(self, sql: str) -> pd.DataFrame:
        """SQL 안의 `bars`를 전체 종목 분봉 테이블로 바꿔 실행합니다. session은 load()와 같은 규칙으로 붙습니다."""
        con = duckdb.connect()
        special = pd.DataFrame(
            [(pd.Timestamp(d).date(), *t) for d, t in SPECIAL_SESSIONS.items()],
            columns=["date", "open_t", "cont_end", "close_t"],
        )
        con.register("special", special)
        o, c, k = DEFAULT_SESSION
        con.execute(f"""
            CREATE VIEW bars AS
            WITH b AS (
                SELECT p.*, strftime(p.ts, '%H:%M') AS hhmm,
                       coalesce(s.open_t, '{o}') AS open_t,
                       coalesce(s.cont_end, '{c}') AS cont_end,
                       coalesce(s.close_t, '{k}') AS close_t
                FROM read_parquet('{self.base.as_posix()}/*/bars.parquet', hive_partitioning = true) p
                LEFT JOIN special s ON s.date = p.ts::DATE
            )
            SELECT * EXCLUDE (hhmm, open_t, cont_end, close_t),
                   CASE WHEN hhmm < open_t THEN 'pre'
                        WHEN hhmm < cont_end THEN 'regular'
                        WHEN ts >= ts::DATE + close_t::TIME
                         AND ts < ts::DATE + close_t::TIME + INTERVAL {CLOSE_WINDOW_MIN} MINUTE THEN 'close'
                        ELSE 'after' END AS session
            FROM b
        """)
        return con.execute(sql).df()
