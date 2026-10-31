# kr-daytrading-ai-tutorial

위키독스 책 [『AI로 검증하는 국내 주식 데이트레이딩 자동매매 따라하기』](https://wikidocs.net/book/21939)의 예제 코드입니다.

트레이딩뷰·Pine Script로 ORB·VWAP 전략을 만들고, Python과 LightGBM으로 검증한 뒤, 키움증권 REST API 모의투자로 자동매매까지 연결합니다.

## 빠른 시작

```bash
git clone https://github.com/ady95/kr-daytrading-ai-tutorial.git
cd kr-daytrading-ai-tutorial
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -e .
cp .env.example .env               # 키움 모의투자 앱키 입력
python chapters/ch02_kiwoom_api/01_issue_token.py
```

키움 REST API는 등록된 IP에서만 호출됩니다. 실행할 PC의 공인 IP를 키움 Open API 사이트에 먼저 등록하세요.

## 구성

| 경로 | 내용 | 책 |
|---|---|---|
| `src/kiwoom_api/` | 키움 REST·WebSocket 클라이언트 (토큰 캐시, 유량 제한 재시도, 연속조회) | 2장 |
| `chapters/ch02_kiwoom_api/` | 토큰 발급, 기본정보·분봉 조회, 실시간 체결, 유량 제한 실습 | 02-4 ~ 02-6 |

장이 진행되면서 데이터 수집, 전략, 백테스트, LightGBM, 주문·위험관리 코드가 추가됩니다.

## 주의

- `.env`와 `.kiwoom_token_*.json`에는 앱키·접근토큰이 들어 있습니다. 커밋하거나 공유하지 마세요.
- 모든 주문 실습은 모의투자(`KIWOOM_ENV=paper`)를 기준으로 합니다.
- 이 저장소의 전략과 결과는 학습용 예시이며 투자 권유가 아닙니다. 실제 투자 판단과 그 결과의 책임은 투자자 본인에게 있습니다.

## 실행 확인 환경

Python 3.12.3, requests 2.34.2, websockets 17.4, pandas 3.1.0, python-dotenv 1.2.4 (2026-10-31, 키움 REST API 모의투자)
