"""02-4 실습: 접근토큰 발급

실행: python chapters/ch02_kiwoom_api/01_issue_token.py
"""

from kiwoom_api import KiwoomClient

client = KiwoomClient()
data = client.issue_token()

token = data["token"]
print(f"환경        : {client.env} ({client.host})")
print(f"결과        : [{data['return_code']}] {data['return_msg']}")
print(f"토큰 유형   : {data['token_type']}")
print(f"토큰        : {token[:6]}...{token[-4:]} ({len(token)}자)")  # 토큰 전체를 화면에 남기지 않는다
print(f"만료 시각   : {client._token_expires:%Y-%m-%d %H:%M:%S}")
