"""키움증권 REST API 클라이언트 (모의투자·실전투자 공용)

- 접근토큰을 파일(.kiwoom_token_<env>.json)에 캐시해 두고 만료 1분 전에 자동으로 다시 발급합니다.
- 유량 제한(HTTP 429, return_code 5)에 걸리면 잠시 쉬었다가 같은 요청을 다시 보냅니다.
- 연속조회(cont-yn / next-key)를 끝까지 따라가는 request_all()을 제공합니다.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

HOSTS = {
    "paper": "https://mockapi.kiwoom.com",  # 모의투자
    "real": "https://api.kiwoom.com",  # 실전투자
}


class KiwoomError(Exception):
    """return_code가 0이 아닌 응답"""

    def __init__(self, api_id: str, return_code: int, return_msg: str):
        super().__init__(f"{api_id} 실패 [{return_code}] {return_msg}")
        self.api_id = api_id
        self.return_code = return_code
        self.return_msg = return_msg


class KiwoomClient:
    def __init__(self, env: str | None = None, max_retries: int = 5):
        load_dotenv()
        self.env = env or os.getenv("KIWOOM_ENV", "paper")
        prefix = f"KIWOOM_{self.env.upper()}_"
        self.app_key = os.environ[prefix + "APP_KEY"]
        self.app_secret = os.environ[prefix + "APP_SECRET"]
        self.account_no = os.getenv(prefix + "ACCOUNT_NO")
        self.host = HOSTS[self.env]
        self.max_retries = max_retries
        self.session = requests.Session()
        self._token: str | None = None
        self._token_expires: datetime | None = None
        self.retry_count = 0  # 유량 제한으로 다시 보낸 횟수 (관찰용)

    # ---- 접근토큰 -------------------------------------------------------
    def issue_token(self) -> dict:
        """au10001: 접근토큰 발급. 응답 원문(토큰 포함)을 돌려주고 파일에 캐시합니다."""
        for attempt in range(self.max_retries + 1):
            r = self.session.post(
                f"{self.host}/oauth2/token",
                headers={"Content-Type": "application/json;charset=UTF-8"},
                json={
                    "grant_type": "client_credentials",
                    "appkey": self.app_key,
                    "secretkey": self.app_secret,
                },
                timeout=10,
            )
            data = r.json()
            if r.status_code == 429 or data.get("return_code") == 5:
                self.retry_count += 1
                time.sleep(0.5 * 2**attempt)
                continue
            break
        if data.get("return_code") != 0:
            raise KiwoomError("au10001", data.get("return_code"), data.get("return_msg"))
        self._token = data["token"]
        self._token_expires = datetime.strptime(data["expires_dt"], "%Y%m%d%H%M%S")
        self._token_file.write_text(json.dumps({"token": self._token, "expires_dt": data["expires_dt"]}))
        self._token_file.chmod(0o600)
        return data

    @property
    def _token_file(self) -> Path:
        return Path(f".kiwoom_token_{self.env}.json")

    def _load_cached_token(self) -> None:
        """스크립트마다 토큰을 새로 받으면 au10001도 유량 제한에 걸리므로, 만료 전 토큰을 재사용합니다."""
        if self._token is None and self._token_file.exists():
            cached = json.loads(self._token_file.read_text())
            self._token = cached["token"]
            self._token_expires = datetime.strptime(cached["expires_dt"], "%Y%m%d%H%M%S")

    @property
    def token(self) -> str:
        self._load_cached_token()
        if self._token is None or datetime.now() >= self._token_expires - timedelta(minutes=1):
            self.issue_token()
        return self._token

    # ---- 일반 요청 ------------------------------------------------------
    def request(self, api_id: str, path: str, body: dict, next_key: str = "") -> tuple[dict, str]:
        """TR 한 번 호출. (응답 본문, 다음 페이지 키)를 돌려주며, 마지막 페이지면 키는 빈 문자열입니다."""
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"Bearer {self.token}",
            "api-id": api_id,
            "cont-yn": "Y" if next_key else "N",
            "next-key": next_key,
        }
        for attempt in range(self.max_retries + 1):
            r = self.session.post(f"{self.host}{path}", headers=headers, json=body, timeout=10)
            data = r.json()
            if r.status_code == 429 or data.get("return_code") == 5:
                # 유량 제한: 0.5s, 1s, 2s ... 쉬었다가 같은 요청을 다시 보낸다
                self.retry_count += 1
                time.sleep(0.5 * 2**attempt)
                continue
            if data.get("return_code") != 0:
                raise KiwoomError(api_id, data.get("return_code"), data.get("return_msg"))
            more = r.headers.get("cont-yn") == "Y"
            return data, r.headers.get("next-key", "") if more else ""
        raise KiwoomError(api_id, 5, "유량 제한 재시도 횟수 초과")

    def request_all(
        self,
        api_id: str,
        path: str,
        body: dict,
        list_key: str,
        max_pages: int | None = None,
        interval: float = 0.3,
    ) -> list[dict]:
        """연속조회를 끝까지(또는 max_pages까지) 따라가며 list_key 목록을 모두 모읍니다."""
        rows: list[dict] = []
        next_key, page = "", 0
        while True:
            data, next_key = self.request(api_id, path, body, next_key)
            rows += data.get(list_key, [])
            page += 1
            if not next_key or (max_pages and page >= max_pages):
                return rows
            time.sleep(interval)


def to_price(value: str) -> int:
    """'-220500', '+238000' 같은 등락 부호가 붙은 가격을 정수로 바꿉니다."""
    return abs(int(value)) if value else 0
