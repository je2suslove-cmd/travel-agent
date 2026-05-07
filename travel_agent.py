"""
AI 여행 일정 플래너 (오프라인 버전)
=====================================
API 키 없이 동작하는 인터랙티브 여행 일정 생성기
"""
from __future__ import annotations

import json
import os
import textwrap
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta


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
    price: int
    seats_left: int


@dataclass
class Hotel:
    name: str
    stars: int
    location: str
    price_per_night: int
    amenities: list[str]
    rating: float
    total_price: int = 0


@dataclass
class Restaurant:
    name: str
    address: str
    rating: float
    review_count: int
    price_level: int   # 0~4, -1=정보없음
    place_id: str


@dataclass
class Attraction:
    name: str
    address: str
    rating: float
    review_count: int
    place_id: str


_PRICE_LEVEL: dict[int, str] = {-1: "", 0: "무료", 1: "₩", 2: "₩₩", 3: "₩₩₩", 4: "₩₩₩₩"}


# ─────────────────────────────────────────────
# Mock 데이터
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
        dict(airline="캐세이퍼시픽",  flight_no="CX417",  departure="서울(ICN)", arrival="홍콩(HKG)", dep_time="08:40", arr_time="11:50", duration="3h50m", base_price=380_000, seats=20),
        dict(airline="대한항공",      flight_no="KE601",  departure="서울(ICN)", arrival="홍콩(HKG)", dep_time="11:00", arr_time="14:05", duration="3h45m", base_price=330_000, seats=25),
        dict(airline="홍콩익스프레스", flight_no="UO808", departure="서울(ICN)", arrival="홍콩(HKG)", dep_time="15:00", arr_time="18:05", duration="3h45m", base_price=240_000, seats=38),
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

_HOTEL_DB: dict[str, dict[str, list[dict]]] = {
    "휴양": {
        "도쿄": [
            dict(name="파크 하얏트 도쿄",       stars=5, location="신주쿠",     ppn=450_000, amenities=["수영장", "스파", "피트니스", "레스토랑"], rating=4.8),
            dict(name="더 프린스 파크 타워",     stars=4, location="미나토",     ppn=280_000, amenities=["수영장", "스파", "바", "레스토랑"],       rating=4.5),
            dict(name="도쿄 그랜드 호텔",        stars=3, location="신바시",     ppn=155_000, amenities=["피트니스", "레스토랑"],                   rating=4.2),
        ],
        "방콕": [
            dict(name="만다린 오리엔탈 방콕",    stars=5, location="차오프라야", ppn=680_000, amenities=["수영장", "스파", "강변전망", "레스토랑"],  rating=4.9),
            dict(name="아마리 워터게이트",       stars=4, location="프라투남",   ppn=320_000, amenities=["수영장", "스파", "루프탑바"],              rating=4.6),
            dict(name="노보텔 방콕 수쿰빗",      stars=3, location="수쿰빗",     ppn=180_000, amenities=["수영장", "피트니스", "레스토랑"],           rating=4.3),
        ],
        "파리": [
            dict(name="르 브리스톨 파리",        stars=5, location="오페라",     ppn=1_200_000, amenities=["수영장", "스파", "미슐랭 레스토랑"],     rating=4.9),
            dict(name="호텔 루브르",             stars=4, location="루브르 근처",ppn=520_000,   amenities=["스파", "레스토랑", "전망"],              rating=4.6),
            dict(name="시타딘 레 할레 파리",     stars=3, location="레알",       ppn=290_000,   amenities=["피트니스", "레스토랑"],                  rating=4.3),
        ],
        "제주": [
            dict(name="신라호텔 제주",           stars=5, location="중문",       ppn=480_000, amenities=["수영장", "스파", "골프", "레스토랑"],      rating=4.8),
            dict(name="해비치 호텔 제주",        stars=4, location="표선",       ppn=280_000, amenities=["수영장", "해변", "스파"],                  rating=4.6),
            dict(name="제주 스타호텔",           stars=3, location="제주시",     ppn=145_000, amenities=["수영장", "레스토랑"],                     rating=4.2),
        ],
        "오사카": [
            dict(name="인터컨티넨탈 오사카",     stars=5, location="우메다",     ppn=420_000, amenities=["수영장", "스파", "레스토랑"],              rating=4.7),
            dict(name="크로스 호텔 오사카",      stars=4, location="난바",       ppn=230_000, amenities=["스파", "레스토랑", "바"],                  rating=4.5),
            dict(name="도미 인 난바",            stars=3, location="난바",       ppn=130_000, amenities=["온천", "레스토랑"],                       rating=4.4),
        ],
        "싱가포르": [
            dict(name="마리나 베이 샌즈",        stars=5, location="마리나 베이", ppn=900_000,   amenities=["인피니티풀", "카지노", "스파", "레스토랑"], rating=4.8),
            dict(name="풀러턴 호텔 싱가포르",    stars=5, location="CBD",         ppn=650_000,   amenities=["수영장", "스파", "리버뷰"],               rating=4.7),
            dict(name="파크 로얄 피커링",        stars=4, location="클락키",      ppn=380_000,   amenities=["수영장", "스파", "정원"],                 rating=4.5),
        ],
        "발리": [
            dict(name="포시즌스 리조트 발리",    stars=5, location="짐바란",      ppn=1_200_000, amenities=["인피니티풀", "스파", "전용해변", "빌라"], rating=4.9),
            dict(name="우부드 하노마 리조트",    stars=4, location="우부드",      ppn=350_000,   amenities=["수영장", "스파", "정글뷰"],               rating=4.7),
            dict(name="코마네카 앳 비스마",      stars=4, location="우부드",      ppn=280_000,   amenities=["수영장", "스파", "요가"],                 rating=4.6),
        ],
        "홍콩": [
            dict(name="더 페닌슐라 홍콩",        stars=5, location="침사추이",    ppn=1_100_000, amenities=["수영장", "스파", "헬리패드", "레스토랑"], rating=4.9),
            dict(name="인터컨티넨탈 홍콩",       stars=5, location="침사추이",    ppn=750_000,   amenities=["수영장", "스파", "항구 뷰"],              rating=4.7),
            dict(name="로얄 플라자 호텔",        stars=4, location="몽콕",        ppn=350_000,   amenities=["수영장", "피트니스", "레스토랑"],         rating=4.4),
        ],
        "뉴욕": [
            dict(name="더 플라자 호텔",          stars=5, location="미드타운",    ppn=2_200_000, amenities=["스파", "피트니스", "레스토랑", "쇼핑"],  rating=4.8),
            dict(name="킴튼 마르탱 호텔",        stars=4, location="첼시",        ppn=850_000,   amenities=["루프탑바", "피트니스", "레스토랑"],       rating=4.5),
            dict(name="인디고 LIC 호텔",         stars=3, location="퀸스",        ppn=520_000,   amenities=["피트니스", "레스토랑", "맨해튼 뷰"],      rating=4.2),
        ],
        "다낭": [
            dict(name="인터컨티넨탈 다낭",       stars=5, location="손트라 반도", ppn=800_000,   amenities=["인피니티풀", "스파", "프라이빗 해변"],    rating=4.9),
            dict(name="빈펄 럭셔리 다낭",        stars=5, location="논 워터파크", ppn=580_000,   amenities=["수영장", "스파", "워터파크"],             rating=4.7),
            dict(name="풀만 다낭 비치 리조트",   stars=4, location="미케 해변",   ppn=350_000,   amenities=["수영장", "스파", "해변"],                 rating=4.5),
        ],
    },
    "액티비티": {
        "도쿄": [
            dict(name="시부야 스트림 엑셀 도큐", stars=4, location="시부야",     ppn=250_000, amenities=["피트니스", "시부야 스카이 접근"],          rating=4.5),
            dict(name="선샤인 시티 프린스",      stars=3, location="이케부쿠로", ppn=165_000, amenities=["놀이공원 접근", "쇼핑몰"],                 rating=4.3),
            dict(name="APA 호텔 신주쿠",         stars=3, location="신주쿠",     ppn=118_000, amenities=["교통 접근성"],                           rating=4.0),
        ],
        "제주": [
            dict(name="롯데시티호텔 제주",       stars=4, location="서귀포",     ppn=210_000, amenities=["수영장", "레저 센터"],                    rating=4.5),
            dict(name="메이즈랜드 리조트",       stars=3, location="함덕",       ppn=150_000, amenities=["수영장", "액티비티 클럽"],                rating=4.3),
            dict(name="제주 한화 리조트",        stars=3, location="중문",       ppn=135_000, amenities=["수영장", "스포츠 시설"],                  rating=4.1),
        ],
        "싱가포르": [
            dict(name="하드록 호텔 센토사",      stars=4, location="센토사",     ppn=380_000, amenities=["수영장", "유니버설 접근", "워터파크"],    rating=4.5),
            dict(name="이비스 벤쿨렌",           stars=3, location="부기스",     ppn=200_000, amenities=["교통 편의", "시내 접근"],                 rating=4.0),
        ],
        "발리": [
            dict(name="더블트리 리조트 꾸따",    stars=4, location="꾸따",        ppn=260_000, amenities=["수영장", "서핑 접근", "레스토랑"],        rating=4.4),
            dict(name="에코 발리 클럽",          stars=3, location="꾸따",        ppn=160_000, amenities=["수영장", "액티비티 센터"],               rating=4.2),
        ],
        "홍콩": [
            dict(name="노보텔 시티게이트",       stars=4, location="란타우",     ppn=310_000, amenities=["수영장", "디즈니랜드 접근"],             rating=4.3),
            dict(name="리갈 에어포트 호텔",      stars=4, location="란타우",     ppn=280_000, amenities=["수영장", "피트니스"],                    rating=4.2),
        ],
        "뉴욕": [
            dict(name="AC 호텔 타임스퀘어",      stars=4, location="타임스퀘어", ppn=780_000, amenities=["피트니스", "루프탑", "교통 편의"],        rating=4.4),
            dict(name="시티즌M 뉴욕",            stars=3, location="타임스퀘어", ppn=580_000, amenities=["루프탑 바", "교통 편의"],                 rating=4.2),
        ],
        "다낭": [
            dict(name="미아 리조트 다낭",        stars=4, location="미케 해변",   ppn=280_000, amenities=["수영장", "서핑 클럽", "워터스포츠"],     rating=4.5),
            dict(name="그린 플라자 다낭",        stars=3, location="미케",        ppn=180_000, amenities=["수영장", "레저 시설"],                   rating=4.1),
        ],
    },
    "맛집": {
        "도쿄": [
            dict(name="더 로얄 파크 캔버스 긴자",stars=4, location="긴자",       ppn=320_000, amenities=["미슐랭 거리 접근", "레스토랑"],            rating=4.7),
            dict(name="마이스테이즈 신주쿠",     stars=3, location="신주쿠",     ppn=142_000, amenities=["식당 밀집 지역", "야시장 접근"],           rating=4.4),
            dict(name="도쿄 스테이션 호텔",      stars=5, location="도쿄역",     ppn=520_000, amenities=["최고급 레스토랑", "명소 접근"],            rating=4.9),
        ],
        "오사카": [
            dict(name="크로스 호텔 도톤보리",    stars=4, location="도톤보리",   ppn=260_000, amenities=["맛집 밀집 지역", "레스토랑"],              rating=4.7),
            dict(name="호텔 몬테레이 라 수르",   stars=3, location="신사이바시", ppn=155_000, amenities=["쇼핑 거리", "식당 접근"],                  rating=4.4),
            dict(name="APA 호텔 난바 에키마에",  stars=3, location="난바",       ppn=120_000, amenities=["교통 편의", "야식 거리"],                  rating=4.2),
        ],
        "방콕": [
            dict(name="차트리움 호텔 리버사이드",stars=5, location="차오프라야", ppn=450_000, amenities=["루프탑 레스토랑", "강변 뷰", "스파"],      rating=4.8),
            dict(name="이비스 방콕 수쿰빗",      stars=3, location="수쿰빗",     ppn=165_000, amenities=["야시장 접근", "식당 거리"],                rating=4.3),
            dict(name="홀리데이 인 방콕",        stars=4, location="실롬",       ppn=280_000, amenities=["레스토랑", "수쿰빗 접근"],                 rating=4.5),
        ],
        "싱가포르": [
            dict(name="클락키 아쿠아 호텔",      stars=4, location="클락키",     ppn=340_000, amenities=["강변 뷰", "레스토랑 밀집 지역"],           rating=4.6),
            dict(name="호텔 81 차이나타운",      stars=3, location="차이나타운", ppn=155_000, amenities=["호커센터 접근", "교통 편의"],               rating=4.1),
        ],
        "발리": [
            dict(name="알라야 우부드",           stars=4, location="우부드",     ppn=310_000, amenities=["수영장", "레스토랑", "요리 클래스"],       rating=4.7),
            dict(name="세미냑 바이 크로마",      stars=4, location="세미냑",     ppn=350_000, amenities=["수영장", "레스토랑 거리 접근"],             rating=4.5),
        ],
        "홍콩": [
            dict(name="랭함 플레이스 몽콕",      stars=5, location="몽콕",       ppn=480_000, amenities=["레스토랑", "딤섬 거리 접근"],               rating=4.7),
            dict(name="노보텔 네이선 로드",      stars=3, location="침사추이",   ppn=230_000, amenities=["식당 거리", "교통 편의"],                   rating=4.3),
        ],
        "뉴욕": [
            dict(name="르 스크립토 뉴욕",        stars=4, location="첼시",       ppn=820_000, amenities=["맛집 밀집", "첼시마켓 접근"],               rating=4.5),
            dict(name="NYY 스탠튼 호텔",         stars=3, location="로어 이스트", ppn=500_000, amenities=["식당 거리", "교통 편의"],                  rating=4.2),
        ],
        "다낭": [
            dict(name="알라나 다낭 호텔",        stars=4, location="한 시장 인근",ppn=250_000, amenities=["레스토랑", "야시장 접근"],                  rating=4.6),
            dict(name="밀레니엄 리조트 다낭",    stars=3, location="미케 해변",   ppn=200_000, amenities=["레스토랑", "해변 접근"],                    rating=4.3),
        ],
    },
}



# ─────────────────────────────────────────────
# 여행지별 콘텐츠 데이터 (destinations.py 참조)
# ─────────────────────────────────────────────

from destinations import _DEST_DATA, _GENERIC_DEST  # noqa: F401



# ─────────────────────────────────────────────
# 날씨 조회 (Open-Meteo — 무료, API 키 불필요)
# ─────────────────────────────────────────────

_CITY_COORDS: dict[str, tuple[float, float, str]] = {
    "도쿄":     (35.6762,  139.6503, "Asia/Tokyo"),
    "오사카":   (34.6937,  135.5023, "Asia/Tokyo"),
    "방콕":     (13.7563,  100.5018, "Asia/Bangkok"),
    "파리":     (48.8566,    2.3522, "Europe/Paris"),
    "제주":     (33.4996,  126.5312, "Asia/Seoul"),
    "싱가포르": ( 1.3521,  103.8198, "Asia/Singapore"),
    "발리":     (-8.3405,  115.0920, "Asia/Makassar"),
    "홍콩":     (22.3193,  114.1694, "Asia/Hong_Kong"),
    "뉴욕":     (40.7128,  -74.0060, "America/New_York"),
    "다낭":     (16.0544,  108.2022, "Asia/Ho_Chi_Minh"),
}

_WMO_DESC: dict[int, tuple[str, str]] = {
    0:  ("☀️",  "맑음"),
    1:  ("🌤️", "주로 맑음"),
    2:  ("⛅",  "부분 흐림"),
    3:  ("☁️",  "흐림"),
    45: ("🌫️", "안개"),
    48: ("🌫️", "짙은 안개"),
    51: ("🌦️", "약한 이슬비"),
    53: ("🌦️", "이슬비"),
    55: ("🌧️", "강한 이슬비"),
    61: ("🌧️", "약한 비"),
    63: ("🌧️", "비"),
    65: ("🌧️", "강한 비"),
    71: ("❄️",  "약한 눈"),
    73: ("❄️",  "눈"),
    75: ("❄️",  "강한 눈"),
    77: ("🌨️", "싸락눈"),
    80: ("🌦️", "약한 소나기"),
    81: ("🌧️", "소나기"),
    82: ("⛈️",  "강한 소나기"),
    85: ("🌨️", "눈 소나기"),
    86: ("🌨️", "강한 눈 소나기"),
    95: ("⛈️",  "뇌우"),
    96: ("⛈️",  "뇌우+우박"),
    99: ("⛈️",  "강한 뇌우+우박"),
}

_DAY_KO = ["월", "화", "수", "목", "금", "토", "일"]


def fetch_weather(destination: str, start_date: str, nights: int) -> dict | None:
    coords = _CITY_COORDS.get(destination)
    if not coords:
        return None

    lat, lon, timezone = coords
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt   = start_dt + timedelta(days=nights)
    is_forecast = (start_dt - datetime.today()).days <= 15

    try:
        if is_forecast:
            url = (
                "https://api.open-meteo.com/v1/forecast"
                f"?latitude={lat}&longitude={lon}"
                "&daily=temperature_2m_max,temperature_2m_min"
                ",precipitation_probability_max,weathercode"
                f"&timezone={timezone}"
                f"&start_date={start_date}"
                f"&end_date={end_dt.strftime('%Y-%m-%d')}"
            )
            precip_key   = "precipitation_probability_max"
            precip_label = "강수확률"
            precip_unit  = "%"
        else:
            # 예보 가능 범위(16일) 초과 → 전년도 같은 기간 실측값 사용
            try:
                ref_start = start_dt.replace(year=start_dt.year - 1)
                ref_end   = end_dt.replace(year=end_dt.year - 1)
            except ValueError:           # 윤년 2/29 예외 처리
                ref_start = start_dt.replace(year=start_dt.year - 2)
                ref_end   = end_dt.replace(year=end_dt.year - 2)
            url = (
                "https://archive-api.open-meteo.com/v1/archive"
                f"?latitude={lat}&longitude={lon}"
                "&daily=temperature_2m_max,temperature_2m_min"
                ",precipitation_sum,weathercode"
                f"&timezone={timezone}"
                f"&start_date={ref_start.strftime('%Y-%m-%d')}"
                f"&end_date={ref_end.strftime('%Y-%m-%d')}"
            )
            precip_key   = "precipitation_sum"
            precip_label = "강수량"
            precip_unit  = "mm"

        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read())

        daily   = data.get("daily", {})
        t_max   = daily.get("temperature_2m_max", [])
        t_min   = daily.get("temperature_2m_min", [])
        codes   = daily.get("weathercode", [])
        precips = daily.get(precip_key, [])

        days = []
        for i, (mx, mn, code, pr) in enumerate(zip(t_max, t_min, codes, precips)):
            actual_date = (start_dt + timedelta(days=i)).strftime("%Y-%m-%d")
            days.append({
                "date":         actual_date,
                "max_temp":     mx   if mx   is not None else 0.0,
                "min_temp":     mn   if mn   is not None else 0.0,
                "code":         int(code) if code is not None else 0,
                "precip":       pr   if pr   is not None else 0.0,
                "precip_label": precip_label,
                "precip_unit":  precip_unit,
            })

        return {"days": days, "is_forecast": is_forecast}

    except Exception:
        return None


def _clothing_advice(days: list[dict]) -> list[str]:
    if not days:
        return []

    avg_max = sum(d["max_temp"] for d in days) / len(days)
    avg_min = sum(d["min_temp"] for d in days) / len(days)
    avg_t   = (avg_max + avg_min) / 2
    is_pct  = days[0]["precip_unit"] == "%"
    max_pr  = max((d["precip"] for d in days), default=0)
    rainy   = sum(1 for d in days if d["precip"] > (40 if is_pct else 5))
    n       = len(days)

    if avg_t < 0:
        outfit = ["두꺼운 패딩", "방한 부츠", "귀마개·장갑·목도리", "기모 내복"]
    elif avg_t < 10:
        outfit = ["두꺼운 코트", "두꺼운 니트", "긴 바지", "목도리·장갑"]
    elif avg_t < 18:
        outfit = ["가벼운 재킷 or 가디건", "긴팔 티셔츠", "긴 바지"]
    elif avg_t < 24:
        outfit = ["얇은 가디건", "긴팔 or 반팔", "청바지·면바지", "저녁용 얇은 겉옷"]
    elif avg_t < 30:
        outfit = ["반팔 티셔츠", "반바지 or 얇은 바지", "선크림 SPF50+", "모자"]
    else:
        outfit = ["반팔·반바지 필수", "선크림 SPF50+ 필수", "모자·선글라스", "쿨링 스프레이"]

    if is_pct:
        if max_pr >= 60 or rainy >= n // 2:
            outfit.append("우산 필수 🌂")
        elif max_pr >= 30 or rainy > 0:
            outfit.append("접이식 우산 권장 🌂")
    else:
        if max_pr >= 10 or rainy >= n // 2:
            outfit.append("우산 필수 🌂")
        elif max_pr >= 3 or rainy > 0:
            outfit.append("접이식 우산 권장 🌂")

    return outfit


def display_weather(weather: dict, destination: str) -> None:
    days        = weather["days"]
    is_forecast = weather["is_forecast"]
    sep         = "━" * 62
    label       = "실시간 예보" if is_forecast else "전년 동기 기후 참고"

    print(f"\n{sep}")
    print(f"  🌤️  {destination} 날씨  ({label})")
    print(sep)

    if not is_forecast:
        print("  ℹ️  예보 범위(16일) 초과 → 작년 같은 기간 실측값으로 기후 경향을 보여드립니다.\n")

    for i, d in enumerate(days):
        dt       = datetime.strptime(d["date"], "%Y-%m-%d")
        date_str = f"{dt.month}/{dt.day}({_DAY_KO[dt.weekday()]})"
        emoji, desc = _WMO_DESC.get(d["code"], ("🌡️", "정보 없음"))
        pr_str   = f"{d['precip']:.0f}{d['precip_unit']}"

        print(f"  Day {i+1:2d}  {date_str}  {emoji} {desc:<10}"
              f"  🌡️ {d['max_temp']:+.0f}°/{d['min_temp']:+.0f}°C"
              f"  💧 {d['precip_label']} {pr_str}")

    n       = len(days)
    avg_max = sum(d["max_temp"] for d in days) / n
    avg_min = sum(d["min_temp"] for d in days) / n
    print(f"\n  {'─' * 58}")
    print(f"  📊 기간 평균   최고 {avg_max:+.1f}°C  /  최저 {avg_min:+.1f}°C")

    advice = _clothing_advice(days)
    if advice:
        print(f"\n  👗 옷차림 추천")
        for item in advice:
            print(f"     · {item}")


# ─────────────────────────────────────────────
# 항공·호텔 검색
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


def search_hotels(destination: str, nights: int, budget_per_night: int, style: str) -> list[Hotel]:
    style_db = _HOTEL_DB.get(style, _HOTEL_DB["휴양"])
    raw = style_db.get(destination)
    if not raw:
        raw = [
            dict(name=f"{destination} 럭셔리 호텔", stars=5, location=f"{destination} 중심가", ppn=450_000, amenities=["수영장", "스파", "레스토랑"], rating=4.8),
            dict(name=f"{destination} 비즈니스 호텔", stars=4, location=f"{destination} 시내", ppn=220_000, amenities=["피트니스", "레스토랑"], rating=4.4),
            dict(name=f"{destination} 이코노미 호텔", stars=3, location=f"{destination} 외곽", ppn=115_000, amenities=["기본 시설"], rating=4.0),
        ]
    hotels = [
        Hotel(
            name=r["name"], stars=r["stars"], location=r["location"],
            price_per_night=r["ppn"], amenities=r["amenities"], rating=r["rating"],
            total_price=r["ppn"] * nights,
        )
        for r in raw
    ]
    in_budget = [h for h in hotels if h.price_per_night <= budget_per_night]
    return (in_budget if in_budget else hotels)[:3]


# ─────────────────────────────────────────────
# Google Places API  (실제 API 교체 지점)
# 환경변수 GOOGLE_PLACES_KEY 설정 시 활성화
# ─────────────────────────────────────────────

def _places_search(query: str, api_key: str, place_type: str = "") -> list[dict]:
    """Google Places Text Search API 호출 (Legacy API)"""
    params: dict[str, str] = {"query": query, "key": api_key, "language": "ko"}
    if place_type:
        params["type"] = place_type
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        status = data.get("status")
        if status == "ZERO_RESULTS":
            return []
        if status != "OK":
            print(f"  ⚠️  Places API 오류: {status} — {data.get('error_message', '')}")
            return []
        return data.get("results", [])
    except Exception as exc:
        print(f"  ⚠️  Places API 요청 실패: {exc}")
        return []


def search_restaurants_places(destination: str, api_key: str) -> list[Restaurant]:
    """여행지 음식점 실제 검색 — 평점 높은 순 반환"""
    results = _places_search(f"{destination} 맛집 레스토랑", api_key, "restaurant")
    items = [
        Restaurant(
            name=r["name"],
            address=r.get("formatted_address", r.get("vicinity", "주소 정보 없음")),
            rating=r.get("rating", 0.0),
            review_count=r.get("user_ratings_total", 0),
            price_level=r.get("price_level", -1),
            place_id=r.get("place_id", ""),
        )
        for r in results if r.get("name")
    ]
    return sorted(items, key=lambda x: x.rating, reverse=True)[:10]


def search_attractions_places(destination: str, api_key: str) -> list[Attraction]:
    """여행지 관광지 실제 검색 — 평점 높은 순 반환"""
    results = _places_search(f"{destination} 관광지 명소", api_key, "tourist_attraction")
    items = [
        Attraction(
            name=r["name"],
            address=r.get("formatted_address", r.get("vicinity", "주소 정보 없음")),
            rating=r.get("rating", 0.0),
            review_count=r.get("user_ratings_total", 0),
            place_id=r.get("place_id", ""),
        )
        for r in results if r.get("name")
    ]
    return sorted(items, key=lambda x: x.rating, reverse=True)[:10]


def display_restaurants(restaurants: list[Restaurant]) -> None:
    print("\n" + "━" * 62)
    print("  🍽️  추천 음식점  (Google Places · 평점 높은 순)")
    print("━" * 62)
    if not restaurants:
        print("  검색 결과가 없습니다.")
        return
    for i, r in enumerate(restaurants, 1):
        price_str = _PRICE_LEVEL.get(r.price_level, "")
        price_tag = f"  {price_str}" if price_str else ""
        print(f"\n  [{i}] ⭐ {r.rating:.1f}  ({r.review_count:,}개 리뷰){price_tag}")
        print(f"      {r.name}")
        print(f"      📍 {r.address}")


def display_attractions(attractions: list[Attraction]) -> None:
    print("\n" + "━" * 62)
    print("  🗺️  추천 관광지  (Google Places · 평점 높은 순)")
    print("━" * 62)
    if not attractions:
        print("  검색 결과가 없습니다.")
        return
    for i, a in enumerate(attractions, 1):
        print(f"\n  [{i}] ⭐ {a.rating:.1f}  ({a.review_count:,}개 리뷰)")
        print(f"      {a.name}")
        print(f"      📍 {a.address}")


# ─────────────────────────────────────────────
# 일정 생성 엔진
# ─────────────────────────────────────────────

def _build_generic_days(destination: str, style: str, nights: int) -> list[dict]:
    """알려지지 않은 여행지 기본 일정 생성"""
    style_focus = {"휴양": "리조트와 스파 이용", "액티비티": "현지 투어와 체험 프로그램", "맛집": "현지 레스토랑과 시장 탐방"}
    focus = style_focus.get(style, "관광명소 탐방")
    days = []
    for i in range(nights + 1):
        if i == 0:
            days.append({
                "title": f"도착 & 첫인상",
                "morning":   "공항 도착 후 환전, 호텔 체크인 및 주변 탐색",
                "afternoon": f"{destination} 중심가 가볍게 탐방",
                "evening":   "호텔 인근 현지 레스토랑 저녁",
                "night":     "숙소 휴식",
                "cost":      "교통비 + 저녁 식사",
            })
        elif i == nights:
            days.append({
                "title": "마지막 날 & 귀국",
                "morning":   "호텔 체크아웃 전 마지막 산책",
                "afternoon": "기념품 구매 후 공항 이동",
                "evening":   "귀국 탑승",
                "night":     "기내",
                "cost":      "기념품 쇼핑",
            })
        else:
            days.append({
                "title": f"{i+1}일차 — {focus}",
                "morning":   f"{destination} 주요 관광명소 오전 탐방",
                "afternoon": f"{focus} 오후 프로그램",
                "evening":   "현지 맛집 저녁 식사",
                "night":     "야경 명소 방문 또는 숙소 휴식",
                "cost":      "입장료 + 식사 + 교통",
            })
    return days


def generate_itinerary(
    info: dict,
    flight: Flight,
    hotel: Hotel,
    costs: dict,
    restaurants: list[Restaurant] | None = None,
    attractions: list[Attraction] | None = None,
) -> None:
    dest = info["destination"]
    style = info["style"]
    nights = info["nights"]
    total_days = nights + 1
    passengers = info["passengers"]

    dest_info = _DEST_DATA.get(dest, _GENERIC_DEST)
    style_data = dest_info.get(style, dest_info.get("휴양", {"days": [], "tips": [], "packing": []}))

    raw_days: list[dict] = style_data.get("days", [])
    if not raw_days:
        raw_days = _build_generic_days(dest, style, nights)

    # 여행 일수에 맞게 일정 조정
    if len(raw_days) > total_days:
        days = raw_days[:total_days]
    elif len(raw_days) < total_days:
        days = list(raw_days)
        for extra in range(total_days - len(raw_days)):
            days.append({
                "title": f"자유 여행 Day {len(days)+1}",
                "morning":   "원하는 명소 자유 탐방",
                "afternoon": "카페 or 쇼핑몰 여유",
                "evening":   "현지 레스토랑 저녁",
                "night":     "야경 포인트 방문",
                "cost":      "자유 지출",
            })
    else:
        days = raw_days

    start_dt = datetime.strptime(info["start_date"], "%Y-%m-%d")
    tips: list[str] = style_data.get("tips", [])
    packing: list[str] = style_data.get("packing", [])

    sep = "━" * 62

    print("\n" + sep)
    print(f"  📅  {dest} {nights}박 {total_days}일 {style} 여행 일정")
    print(sep)

    # ── 기본 정보 요약
    print(f"\n  ✈️  {flight.airline} {flight.flight_no}  |  {flight.departure} → {flight.arrival}")
    print(f"      출발 {flight.dep_time}  →  도착 {flight.arr_time}  (소요 {flight.duration})")
    print(f"  🏨  {'★' * hotel.stars}  {hotel.name}  ({hotel.location})")
    print(f"  💰  총 예상 비용: {costs['total']:,}원  (예산: {costs['budget']:,}원)")
    if costs["over_budget"]:
        print(f"  ⚠️  예산 {costs['difference']:,}원 초과 — 숙박 등급 조정을 고려해보세요.")
    else:
        print(f"  ✅  예산 {costs['difference']:,}원 여유")

    # ── Day별 일정
    print(f"\n{'─' * 62}")
    print("  [ 상세 일정 ]")
    print(f"{'─' * 62}")

    for i, day in enumerate(days):
        date_str = (start_dt + timedelta(days=i)).strftime("%m월 %d일")
        print(f"\n  ▶  Day {i+1}  ({date_str})  —  {day['title']}")
        print(f"     🌅 오전   {day['morning']}")
        print(f"     ☀️ 오후   {day['afternoon']}")
        print(f"     🌆 저녁   {day['evening']}")
        print(f"     🌙 야간   {day['night']}")
        print(f"     💸 비용   {day['cost']}")

    # ── 현지 꿀팁
    if tips:
        print(f"\n{'─' * 62}")
        print("  [ 현지 실전 꿀팁 ]")
        print(f"{'─' * 62}")
        for tip in tips:
            print(f"  ✔  {tip}")

    # ── 교통·환전 정보
    print(f"\n{'─' * 62}")
    print("  [ 현지 기본 정보 ]")
    print(f"{'─' * 62}")
    print(f"  💱 통화      {dest_info['currency']}")
    print(f"  🏧 환전 팁   {dest_info['exchange_tip']}")
    print(f"  🚇 교통      {dest_info['transport']}")
    print(f"  🔌 플러그    {dest_info['plug']}")
    print(f"  🕐 시차      {dest_info['시차']}")
    print(f"  ☀️ 날씨 팁   {dest_info['계절_팁']}")

    # ── 짐 체크리스트
    if packing:
        print(f"\n{'─' * 62}")
        print("  [ 짐 챙기기 체크리스트 ]")
        print(f"{'─' * 62}")
        for item in packing:
            print(f"  ☐  {item}")
        print(f"  ☐  여권 (유효기간 6개월 이상)")
        print(f"  ☐  여행자 보험 가입 확인")
        print(f"  ☐  현지 비상 연락처 메모")

    # ── 예산 상세 내역
    print(f"\n{'─' * 62}")
    print("  [ 예상 비용 내역 ]")
    print(f"{'─' * 62}")
    print(f"  ✈️  항공권 ({passengers}명)     {costs['flight']:>12,}원")
    print(f"  🏨  숙박 ({nights}박)          {costs['hotel']:>12,}원")
    print(f"  🍽️  식비·교통·관광 (추정)  {costs['misc']:>12,}원")
    print(f"  {'─' * 44}")
    print(f"  💳  총 예상 비용           {costs['total']:>12,}원")
    print(f"  📦  설정 예산              {costs['budget']:>12,}원")

    # ── Google Places 실제 데이터 (API 키 있을 때만 출력)
    if restaurants:
        print(f"\n{'─' * 62}")
        print("  [ 실제 추천 음식점  (Google Places) ]")
        print(f"{'─' * 62}")
        for i, r in enumerate(restaurants[:5], 1):
            price_str = _PRICE_LEVEL.get(r.price_level, "")
            price_tag = f"  {price_str}" if price_str else ""
            print(f"  {i}. ⭐ {r.rating:.1f} ({r.review_count:,}명){price_tag}  {r.name}")
            print(f"     📍 {r.address}")

    if attractions:
        print(f"\n{'─' * 62}")
        print("  [ 실제 추천 관광지  (Google Places) ]")
        print(f"{'─' * 62}")
        for i, a in enumerate(attractions[:5], 1):
            print(f"  {i}. ⭐ {a.rating:.1f} ({a.review_count:,}명)  {a.name}")
            print(f"     📍 {a.address}")


# ─────────────────────────────────────────────
# 입력 수집
# ─────────────────────────────────────────────

def _input_int(prompt: str, min_val: int = 1) -> int:
    while True:
        try:
            v = int(input(prompt).strip().replace(",", ""))
            if v >= min_val:
                return v
        except ValueError:
            pass
        print(f"  ❌ {min_val} 이상의 숫자를 입력해주세요.")


def _input_date(prompt: str) -> str:
    while True:
        s = input(prompt).strip()
        try:
            datetime.strptime(s, "%Y-%m-%d")
            return s
        except ValueError:
            print("  ❌ 올바른 날짜 형식으로 입력해주세요 (예: 2026-07-01)")


def get_user_input() -> dict:
    print("\n" + "=" * 62)
    print("  🌏  AI 여행 일정 플래너에 오신 것을 환영합니다!")
    print("  📌  지원 여행지: 도쿄 · 오사카 · 방콕 · 파리 · 제주")
    print("             싱가포르 · 발리 · 홍콩 · 뉴욕 · 다낭")
    print("=" * 62 + "\n")

    origin      = input("출발지 (예: 서울): ").strip() or "서울"
    destination = input("여행지 (예: 도쿄): ").strip() or "도쿄"
    start_date  = _input_date("출발 날짜 (예: 2026-07-01): ")
    nights      = _input_int("숙박 일수 (예: 4): ")
    passengers  = _input_int("여행 인원 (예: 2): ")
    budget      = _input_int("총 예산 (원, 예: 3000000): ")

    print("\n여행 스타일을 선택해주세요:")
    print("  1. 휴양   2. 액티비티   3. 맛집")
    style_map = {"1": "휴양", "2": "액티비티", "3": "맛집"}
    while True:
        choice = input("선택 (1/2/3): ").strip()
        if choice in style_map:
            style = style_map[choice]
            break
        if choice in style_map.values():
            style = choice
            break
        print("  ❌ 1, 2, 3 중 선택해주세요.")

    end_date = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=nights)).strftime("%Y-%m-%d")

    return dict(
        origin=origin, destination=destination,
        start_date=start_date, end_date=end_date,
        nights=nights, passengers=passengers,
        budget=budget, style=style,
    )


# ─────────────────────────────────────────────
# 결과 출력
# ─────────────────────────────────────────────

def display_flights(flights: list[Flight], passengers: int) -> None:
    print("\n" + "━" * 62)
    print("  ✈️  항공편 검색 결과 (최저가 순)")
    print("━" * 62)
    for i, f in enumerate(flights, 1):
        print(f"\n  [{i}] {f.airline}  {f.flight_no}")
        print(f"      {f.departure}  →  {f.arrival}")
        print(f"      출발 {f.dep_time} | 도착 {f.arr_time} | 소요 {f.duration}")
        print(f"      💰 {f.price:,}원 ({passengers}명 합산)  |  잔여 {f.seats_left}석")


def display_hotels(hotels: list[Hotel], nights: int, ppn_budget: int) -> None:
    print("\n" + "━" * 62)
    print("  🏨  호텔 추천")
    print("━" * 62)
    for i, h in enumerate(hotels, 1):
        tag = "✅ 예산 내" if h.price_per_night <= ppn_budget else "⚠️ 예산 초과"
        stars = "★" * h.stars + "☆" * (5 - h.stars)
        print(f"\n  [{i}] {stars}  {h.name}  {tag}")
        print(f"      📍 {h.location}  |  평점 {h.rating}/5.0")
        print(f"      💰 1박 {h.price_per_night:,}원  →  {nights}박 합계 {h.total_price:,}원")
        print(f"      🛎  {' · '.join(h.amenities)}")


def calculate_costs(flight: Flight, hotel: Hotel, nights: int, passengers: int, budget: int) -> dict:
    misc = passengers * nights * 80_000
    total = flight.price + hotel.total_price + misc
    return dict(
        flight=flight.price, hotel=hotel.total_price,
        misc=misc, total=total, budget=budget,
        over_budget=total > budget,
        difference=abs(total - budget),
    )


# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────

def main() -> None:
    info = get_user_input()

    print("\n🔍 항공편을 검색하고 있습니다...")
    flights = search_flights(info["origin"], info["destination"], info["passengers"])
    display_flights(flights, info["passengers"])
    selected_flight = flights[0]
    print(f"\n  → 최저가 항공편 자동 선택: {selected_flight.airline} {selected_flight.flight_no}  ({selected_flight.price:,}원)")

    remaining_budget = info["budget"] - selected_flight.price
    ppn_budget = max(int(remaining_budget * 0.40 / info["nights"]), 50_000)

    print("\n🔍 호텔을 검색하고 있습니다...")
    hotels = search_hotels(info["destination"], info["nights"], ppn_budget, info["style"])
    display_hotels(hotels, info["nights"], ppn_budget)

    selected_hotel = max(hotels, key=lambda h: (h.price_per_night <= ppn_budget, h.rating))
    print(f"\n  → 추천 호텔 선택: {selected_hotel.name}  (평점 {selected_hotel.rating}/5.0)")

    costs = calculate_costs(selected_flight, selected_hotel, info["nights"], info["passengers"], info["budget"])

    print("\n🔍 날씨 정보를 조회하고 있습니다...")
    weather = fetch_weather(info["destination"], info["start_date"], info["nights"])
    if weather:
        display_weather(weather, info["destination"])
    else:
        print("  ⚠️  날씨 정보를 불러올 수 없습니다. (네트워크 상태 확인)")

    places_key = os.environ.get("GOOGLE_PLACES_KEY")
    restaurants: list[Restaurant] = []
    attractions: list[Attraction] = []
    if places_key:
        print("\n🔍 Google Places API로 음식점·관광지를 검색 중...")
        restaurants = search_restaurants_places(info["destination"], places_key)
        display_restaurants(restaurants)
        attractions = search_attractions_places(info["destination"], places_key)
        display_attractions(attractions)
    else:
        print("\n  ℹ️  GOOGLE_PLACES_KEY 미설정 — 음식점·관광지 실시간 검색 생략")
        print("     (export GOOGLE_PLACES_KEY=your_key 로 설정하면 실제 데이터를 사용합니다)")

    print("\n✍️  맞춤 여행 일정을 생성하고 있습니다...\n")
    generate_itinerary(info, selected_flight, selected_hotel, costs,
                       restaurants=restaurants, attractions=attractions)

    print("\n" + "=" * 62)
    print("  🎉  일정 생성 완료!  즐거운 여행 되세요! ✈️")
    print("=" * 62 + "\n")


if __name__ == "__main__":
    main()
