"""02-5 실습 1: 주식 기본정보 조회 (ka10001)

실행: python chapters/ch02_kiwoom_api/02_stock_info.py 005930
"""

import sys

from kiwoom_api import KiwoomClient, to_price

stk_cd = sys.argv[1] if len(sys.argv) > 1 else "005930"

client = KiwoomClient()
data, _ = client.request("ka10001", "/api/dostk/stkinfo", {"stk_cd": stk_cd})

print(f"{data['stk_nm']} ({data['stk_cd']})")
print(f"  현재가   {to_price(data['cur_prc']):>10,}원  ({data['flu_rt']}%)")
print(f"  시가     {to_price(data['open_pric']):>10,}원")
print(f"  고가     {to_price(data['high_pric']):>10,}원")
print(f"  저가     {to_price(data['low_pric']):>10,}원")
print(f"  기준가   {to_price(data['base_pric']):>10,}원")
print(f"  상한가   {to_price(data['upl_pric']):>10,}원")
print(f"  하한가   {to_price(data['lst_pric']):>10,}원")
print(f"  거래량   {int(data['trde_qty']):>10,}주")
print(f"  원본 cur_prc 값: {data['cur_prc']!r}  <- 앞의 부호는 전일 대비 등락 방향")
