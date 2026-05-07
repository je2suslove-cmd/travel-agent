"""
항공권 검색 에이전트
Mock 데이터 기반 항공편 검색 — search_flights() 내부를 Amadeus/Skyscanner API로 교체 가능
"""
from __future__ import annotations

from dataclasses import dataclass


# ─────────────────────────────────────────────
# 데이터 모델
# ─────────────────────────────────────────────

@dataclass
class Flight:
    airline: str
    flight_no: str
    departure: str
    arrival: str
    dep_time: str
    arr_time: str
    duration: str
    price: int          # 원화, 인원 합산
    seats_left: int


# ─────────────────────────────────────────────
# Mock 데이터  (실제 API 교체 지점 — Amadeus / Skyscanner)
# ─────────────────────────────────────────────

_FLIGHT_DB: dict[tuple[str, str], list[dict]] = {
    ("서울", "도쿄"): [
        dict(airline="대한항공",  flight_no="KE703",  departure="서울(ICN)", arrival="도쿄(NRT)", dep_time="09:00", arr_time="11:30", duration="2h30m", base_price=280_000, seats=12),
        dict(airline="아시아나",  flight_no="OZ101",  departure="서울(ICN)", arrival="도쿄(HND)", dep_time="11:40", arr_time="14:00", duration="2h20m", base_price=245_000, seats=8),
        dict(airline="제주항공",  flight_no="7C1101", departure="서울(ICN)", arrival="도쿄(NRT)", dep_time="15:20", arr_time="17:50", duration="2h30m", base_price=198_000, seats=25),
    ],
    ("서울", "방콕"): [
        dict(airline="대한항공",  flight_no="KE651",  departure="서울(ICN)", arrival="방콕(BKK)", dep_time="10:00", arr_time="14:30", duration="5h30m", base_price=520_000, seats=18),
        dict(airline="타이항공",  flight_no="TG659",  departure="서울(ICN)", arrival="방콕(BKK)", dep_time="13:20", arr_time="18:00", duration="5h40m", base_price=465_000, seats=22),
        dict(airline="진에어",    flight_no="LJ001",  departure="서울(ICN)", arrival="방콕(BKK)", dep_time="06:40", arr_time="11:10", duration="5h30m", base_price=398_000, seats=31),
    ],
    ("서울", "파리"): [
        dict(airline="대한항공",   flight_no="KE901", departure="서울(ICN)", arrival="파리(CDG)", dep_time="13:30", arr_time="18:50", duration="12h20m", base_price=1_250_000, seats=9),
        dict(airline="에어프랑스", flight_no="AF267", departure="서울(ICN)", arrival="파리(CDG)", dep_time="11:00", arr_time="16:30", duration="12h30m", base_price=1_180_000, seats=14),
        dict(airline="루프트한자", flight_no="LH713", departure="서울(ICN)", arrival="파리(CDG)", dep_time="09:45", arr_time="17:20", duration="13h35m", base_price=1_050_000, seats=7),
    ],
    ("서울", "제주"): [
        dict(airline="제주항공", flight_no="7C101",  departure="서울(GMP)", arrival="제주(CJU)", dep_time="07:00", arr_time="08:05", duration="1h05m", base_price=68_000,  seats=45),
        dict(airline="대한항공", flight_no="KE1201", departure="서울(GMP)", arrival="제주(CJU)", dep_time="09:00", arr_time="10:05", duration="1h05m", base_price=82_000,  seats=30),
        dict(airline="아시아나", flight_no="OZ8901", departure="서울(GMP)", arrival="제주(CJU)", dep_time="11:30", arr_time="12:35", duration="1h05m", base_price=75_000,  seats=38),
    ],
    ("서울", "오사카"): [
        dict(airline="대한항공", flight_no="KE723",  departure="서울(ICN)", arrival="오사카(KIX)", dep_time="08:30", arr_time="10:40", duration="2h10m", base_price=260_000, seats=20),
        dict(airline="티웨이",   flight_no="TW201",  departure="서울(ICN)", arrival="오사카(KIX)", dep_time="14:00", arr_time="16:10", duration="2h10m", base_price=185_000, seats=35),
        dict(airline="피치항공", flight_no="MM201",  departure="서울(ICN)", arrival="오사카(KIX)", dep_time="17:30", arr_time="19:40", duration="2h10m", base_price=155_000, seats=42),
    ],
    ("서울", "싱가포르"): [
        dict(airline="싱가포르항공", flight_no="SQ601", departure="서울(ICN)", arrival="싱가포르(SIN)", dep_time="09:30", arr_time="15:30", duration="6h30m", base_price=620_000, seats=15),
        dict(airline="대한항공",     flight_no="KE643", departure="서울(ICN)", arrival="싱가포르(SIN)", dep_time="17:20", arr_time="23:20", duration="6h30m", base_price=570_000, seats=20),
        dict(airline="스쿠트",       flight_no="TR869", departure="서울(ICN)", arrival="싱가포르(SIN)", dep_time="22:00", arr_time="04:10", duration="6h40m", base_price=390_000, seats=40),
    ],
    ("서울", "발리"): [
        dict(airline="대한항공",   flight_no="KE629", departure="서울(ICN)", arrival="발리(DPS)", dep_time="08:00", arr_time="14:20", duration="7h20m", base_price=680_000, seats=18),
        dict(airline="가루다항공", flight_no="GA878", departure="서울(ICN)", arrival="발리(DPS)", dep_time="12:00", arr_time="18:30", duration="7h30m", base_price=610_000, seats=22),
        dict(airline="에어아시아", flight_no="AK783", departure="서울(ICN)", arrival="발리(DPS)", dep_time="06:00", arr_time="13:00", duration="8h00m", base_price=480_000, seats=35),
    ],
    ("서울", "홍콩"): [
        dict(airline="캐세이퍼시픽",   flight_no="CX417",  departure="서울(ICN)", arrival="홍콩(HKG)", dep_time="08:40", arr_time="11:50", duration="3h50m", base_price=380_000, seats=20),
        dict(airline="대한항공",       flight_no="KE601",  departure="서울(ICN)", arrival="홍콩(HKG)", dep_time="11:00", arr_time="14:05", duration="3h45m", base_price=330_000, seats=25),
        dict(airline="홍콩익스프레스", flight_no="UO808",  departure="서울(ICN)", arrival="홍콩(HKG)", dep_time="15:00", arr_time="18:05", duration="3h45m", base_price=240_000, seats=38),
    ],
    ("서울", "뉴욕"): [
        dict(airline="대한항공",   flight_no="KE081", departure="서울(ICN)", arrival="뉴욕(JFK)", dep_time="10:00", arr_time="10:30", duration="14h30m", base_price=1_580_000, seats=12),
        dict(airline="아시아나",   flight_no="OZ221", departure="서울(ICN)", arrival="뉴욕(JFK)", dep_time="13:40", arr_time="14:10", duration="14h30m", base_price=1_450_000, seats=16),
        dict(airline="유나이티드", flight_no="UA892", departure="서울(ICN)", arrival="뉴욕(EWR)", dep_time="18:00", arr_time="18:30", duration="14h30m", base_price=1_280_000, seats=22),
    ],
    ("서울", "다낭"): [
        dict(airline="대한항공", flight_no="KE463",  departure="서울(ICN)", arrival="다낭(DAD)", dep_time="09:00", arr_time="12:30", duration="4h30m", base_price=460_000, seats=22),
        dict(airline="비엣젯",   flight_no="VJ870",  departure="서울(ICN)", arrival="다낭(DAD)", dep_time="13:00", arr_time="16:40", duration="4h40m", base_price=320_000, seats=40),
        dict(airline="제주항공", flight_no="7C3303", departure="서울(ICN)", arrival="다낭(DAD)", dep_time="07:00", arr_time="10:30", duration="4h30m", base_price=350_000, seats=30),
    ],
}


# ─────────────────────────────────────────────
# 검색·출력
# ─────────────────────────────────────────────

def search_flights(origin: str, destination: str, passengers: int) -> list[Flight]:
    raw = _FLIGHT_DB.get((origin, destination))
    if not raw:
        raw = [
            dict(airline="대한항공", flight_no="KE999", departure=f"{origin}(ICN)", arrival=f"{destination}(INT)", dep_time="10:00", arr_time="14:00", duration="4h00m", base_price=650_000, seats=20),
            dict(airline="아시아나", flight_no="OZ999", departure=f"{origin}(ICN)", arrival=f"{destination}(INT)", dep_time="13:00", arr_time="17:00", duration="4h00m", base_price=580_000, seats=15),
            dict(airline="저가항공", flight_no="LJ999", departure=f"{origin}(ICN)", arrival=f"{destination}(INT)", dep_time="16:00", arr_time="20:00", duration="4h00m", base_price=450_000, seats=35),
        ]
    result = [
        Flight(
            airline=r["airline"], flight_no=r["flight_no"],
            departure=r["departure"], arrival=r["arrival"],
            dep_time=r["dep_time"], arr_time=r["arr_time"],
            duration=r["duration"],
            price=r["base_price"] * passengers,
            seats_left=r["seats"],
        )
        for r in raw
    ]
    return sorted(result, key=lambda f: f.price)


def display_flights(flights: list[Flight], passengers: int) -> None:
    print("\n" + "━" * 62)
    print("  ✈️  항공편 검색 결과 (최저가 순)")
    print("━" * 62)
    for i, f in enumerate(flights, 1):
        print(f"\n  [{i}] {f.airline}  {f.flight_no}")
        print(f"      {f.departure}  →  {f.arrival}")
        print(f"      출발 {f.dep_time} | 도착 {f.arr_time} | 소요 {f.duration}")
        print(f"      💰 {f.price:,}원 ({passengers}명 합산)  |  잔여 {f.seats_left}석")


def run(origin: str, destination: str, passengers: int) -> list[Flight]:
    return search_flights(origin, destination, passengers)
