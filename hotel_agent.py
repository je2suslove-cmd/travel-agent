"""
호텔 검색 에이전트
Google Places Nearby Search API로 실제 호텔 이름·평점·위치 조회
GOOGLE_PLACES_KEY 없으면 Mock 데이터로 자동 폴백
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass


# ─────────────────────────────────────────────
# 데이터 모델
# ─────────────────────────────────────────────

@dataclass
class Hotel:
    name: str
    stars: int
    location: str
    price_per_night: int
    amenities: list[str]
    rating: float
    total_price: int = 0


# ─────────────────────────────────────────────
# Mock 데이터  (실제 API 교체 지점 — Booking.com / Hotels.com)
# ─────────────────────────────────────────────

_HOTEL_DB: dict[str, dict[str, list[dict]]] = {
    "휴양": {
        "도쿄": [
            dict(name="파크 하얏트 도쿄",        stars=5, location="신주쿠",     ppn=450_000, amenities=["수영장", "스파", "피트니스", "레스토랑"],   rating=4.8),
            dict(name="그랜드 하얏트 도쿄",      stars=5, location="롯폰기",     ppn=520_000, amenities=["수영장", "스파", "5개 레스토랑"],          rating=4.7),
            dict(name="더 프린스 파크 타워",     stars=4, location="미나토",     ppn=280_000, amenities=["수영장", "스파", "바", "레스토랑"],         rating=4.5),
            dict(name="도쿄 그랜드 호텔",        stars=3, location="신바시",     ppn=155_000, amenities=["피트니스", "레스토랑"],                    rating=4.2),
            dict(name="도쿄 가든 팰리스",        stars=3, location="분쿄",       ppn=118_000, amenities=["레스토랑", "조식 포함"],                   rating=4.0),
        ],
        "방콕": [
            dict(name="만다린 오리엔탈 방콕",    stars=5, location="차오프라야", ppn=680_000, amenities=["수영장", "스파", "강변전망", "레스토랑"],   rating=4.9),
            dict(name="JW 메리어트 방콕",        stars=5, location="수쿰빗",     ppn=580_000, amenities=["수영장", "스파", "피트니스", "클럽라운지"], rating=4.7),
            dict(name="아마리 워터게이트",       stars=4, location="프라투남",   ppn=320_000, amenities=["수영장", "스파", "루프탑바"],              rating=4.6),
            dict(name="노보텔 방콕 수쿰빗",      stars=3, location="수쿰빗",     ppn=180_000, amenities=["수영장", "피트니스", "레스토랑"],           rating=4.3),
            dict(name="이비스 방콕 낙싸완",      stars=3, location="차이나타운", ppn=110_000, amenities=["피트니스", "레스토랑"],                    rating=4.0),
        ],
        "파리": [
            dict(name="르 브리스톨 파리",        stars=5, location="오페라",       ppn=1_200_000, amenities=["수영장", "스파", "미슐랭 레스토랑"],   rating=4.9),
            dict(name="소피텔 파리 르 포브르",   stars=5, location="루브르 근처",  ppn=750_000,   amenities=["스파", "피트니스", "루브르 전망"],      rating=4.7),
            dict(name="호텔 루브르",             stars=4, location="루브르 근처",  ppn=520_000,   amenities=["스파", "레스토랑", "전망"],             rating=4.6),
            dict(name="르 메리디앙 에투알",      stars=4, location="샹젤리제",     ppn=420_000,   amenities=["피트니스", "레스토랑", "바"],           rating=4.4),
            dict(name="시타딘 레 할레 파리",     stars=3, location="레알",         ppn=290_000,   amenities=["피트니스", "레스토랑"],                 rating=4.3),
        ],
        "제주": [
            dict(name="신라호텔 제주",           stars=5, location="중문",       ppn=480_000, amenities=["수영장", "스파", "골프", "레스토랑"],      rating=4.8),
            dict(name="롯데호텔 제주",           stars=5, location="중문",       ppn=380_000, amenities=["수영장", "스파", "워터파크", "레스토랑"],  rating=4.7),
            dict(name="해비치 호텔 제주",        stars=4, location="표선",       ppn=280_000, amenities=["수영장", "해변", "스파"],                  rating=4.6),
            dict(name="제주 스타호텔",           stars=3, location="제주시",     ppn=145_000, amenities=["수영장", "레스토랑"],                     rating=4.2),
            dict(name="씨에스 호텔앤리조트",     stars=3, location="성산",       ppn=98_000,  amenities=["레스토랑", "해변 접근"],                   rating=4.0),
        ],
        "오사카": [
            dict(name="인터컨티넨탈 오사카",     stars=5, location="우메다",     ppn=420_000, amenities=["수영장", "스파", "레스토랑"],              rating=4.7),
            dict(name="힐튼 오사카",             stars=5, location="우메다",     ppn=380_000, amenities=["수영장", "피트니스", "레스토랑", "바"],    rating=4.6),
            dict(name="크로스 호텔 오사카",      stars=4, location="난바",       ppn=230_000, amenities=["스파", "레스토랑", "바"],                  rating=4.5),
            dict(name="도미 인 난바",            stars=3, location="난바",       ppn=130_000, amenities=["온천", "레스토랑"],                       rating=4.4),
            dict(name="도요코인 신오사카역",     stars=2, location="신오사카",   ppn=78_000,  amenities=["조식 포함", "교통 편의"],                  rating=4.0),
        ],
        "싱가포르": [
            dict(name="마리나 베이 샌즈",        stars=5, location="마리나 베이", ppn=900_000,   amenities=["인피니티풀", "카지노", "스파", "레스토랑"], rating=4.8),
            dict(name="만다린 오리엔탈 싱가포르",stars=5, location="마리나",      ppn=820_000,   amenities=["수영장", "스파", "리버뷰", "미슐랭"],      rating=4.7),
            dict(name="풀러턴 호텔 싱가포르",    stars=5, location="CBD",         ppn=650_000,   amenities=["수영장", "스파", "리버뷰"],               rating=4.7),
            dict(name="파크 로얄 피커링",        stars=4, location="클락키",      ppn=380_000,   amenities=["수영장", "스파", "정원"],                 rating=4.5),
            dict(name="파크로얄 비치 로드",      stars=3, location="비치 로드",   ppn=280_000,   amenities=["수영장", "피트니스"],                     rating=4.2),
        ],
        "발리": [
            dict(name="포시즌스 리조트 발리",    stars=5, location="짐바란",      ppn=1_200_000, amenities=["인피니티풀", "스파", "전용해변", "빌라"], rating=4.9),
            dict(name="콘래드 발리",             stars=5, location="짐바란",      ppn=850_000,   amenities=["수영장", "스파", "전용해변", "레스토랑"], rating=4.8),
            dict(name="우부드 하노마 리조트",    stars=4, location="우부드",      ppn=350_000,   amenities=["수영장", "스파", "정글뷰"],               rating=4.7),
            dict(name="코마네카 앳 비스마",      stars=4, location="우부드",      ppn=280_000,   amenities=["수영장", "스파", "요가"],                 rating=4.6),
            dict(name="에코 발리 리조트",        stars=3, location="꾸따",        ppn=140_000,   amenities=["수영장", "서핑 접근"],                    rating=4.1),
        ],
        "홍콩": [
            dict(name="더 페닌슐라 홍콩",        stars=5, location="침사추이",    ppn=1_100_000, amenities=["수영장", "스파", "헬리패드", "레스토랑"], rating=4.9),
            dict(name="만다린 오리엔탈 홍콩",    stars=5, location="센트럴",      ppn=980_000,   amenities=["수영장", "스파", "미슐랭 레스토랑"],      rating=4.8),
            dict(name="인터컨티넨탈 홍콩",       stars=5, location="침사추이",    ppn=750_000,   amenities=["수영장", "스파", "항구 뷰"],              rating=4.7),
            dict(name="로얄 플라자 호텔",        stars=4, location="몽콕",        ppn=350_000,   amenities=["수영장", "피트니스", "레스토랑"],         rating=4.4),
            dict(name="하버 플라자 노스 포인트", stars=3, location="노스포인트",  ppn=190_000,   amenities=["수영장", "피트니스"],                     rating=4.0),
        ],
        "뉴욕": [
            dict(name="더 플라자 호텔",          stars=5, location="미드타운",    ppn=2_200_000, amenities=["스파", "피트니스", "레스토랑", "쇼핑"],  rating=4.8),
            dict(name="포시즌스 뉴욕",           stars=5, location="미드타운",    ppn=2_800_000, amenities=["수영장", "스파", "피트니스", "레스토랑"], rating=4.9),
            dict(name="킴튼 마르탱 호텔",        stars=4, location="첼시",        ppn=850_000,   amenities=["루프탑바", "피트니스", "레스토랑"],       rating=4.5),
            dict(name="인디고 LIC 호텔",         stars=3, location="퀸스",        ppn=520_000,   amenities=["피트니스", "레스토랑", "맨해튼 뷰"],      rating=4.2),
            dict(name="알로프트 브루클린",       stars=3, location="브루클린",    ppn=390_000,   amenities=["피트니스", "바", "레스토랑"],              rating=4.1),
        ],
        "다낭": [
            dict(name="인터컨티넨탈 다낭",       stars=5, location="손트라 반도", ppn=800_000,   amenities=["인피니티풀", "스파", "프라이빗 해변"],    rating=4.9),
            dict(name="JW 메리어트 다낭",        stars=5, location="미케 해변",   ppn=950_000,   amenities=["수영장", "스파", "전용해변", "레스토랑"], rating=4.8),
            dict(name="빈펄 럭셔리 다낭",        stars=5, location="논 워터파크", ppn=580_000,   amenities=["수영장", "스파", "워터파크"],             rating=4.7),
            dict(name="풀만 다낭 비치 리조트",   stars=4, location="미케 해변",   ppn=350_000,   amenities=["수영장", "스파", "해변"],                 rating=4.5),
            dict(name="머큐어 다낭",             stars=3, location="한강변",      ppn=220_000,   amenities=["수영장", "피트니스", "강변 뷰"],          rating=4.2),
        ],
    },
    "액티비티": {
        "도쿄": [
            dict(name="시부야 스트림 엑셀 도큐", stars=4, location="시부야",     ppn=250_000, amenities=["피트니스", "시부야 스카이 접근"],          rating=4.5),
            dict(name="호텔 그레이스리 신주쿠",  stars=4, location="신주쿠",     ppn=185_000, amenities=["가부키초 접근", "레스토랑"],               rating=4.3),
            dict(name="선샤인 시티 프린스",      stars=3, location="이케부쿠로", ppn=165_000, amenities=["놀이공원 접근", "쇼핑몰"],                 rating=4.3),
            dict(name="APA 호텔 신주쿠",         stars=3, location="신주쿠",     ppn=118_000, amenities=["교통 접근성"],                           rating=4.0),
            dict(name="캡슐 인 신주쿠",          stars=2, location="신주쿠",     ppn=65_000,  amenities=["공중욕장", "코인 세탁기"],                rating=3.8),
        ],
        "제주": [
            dict(name="롯데시티호텔 제주",       stars=4, location="서귀포",     ppn=210_000, amenities=["수영장", "레저 센터"],                    rating=4.5),
            dict(name="제주 오리엔탈 호텔",      stars=4, location="노형동",     ppn=180_000, amenities=["수영장", "피트니스", "렌터카 안내"],      rating=4.4),
            dict(name="메이즈랜드 리조트",       stars=3, location="함덕",       ppn=150_000, amenities=["수영장", "액티비티 클럽"],                rating=4.3),
            dict(name="제주 한화 리조트",        stars=3, location="중문",       ppn=135_000, amenities=["수영장", "스포츠 시설"],                  rating=4.1),
            dict(name="서귀포 칼 호텔",          stars=3, location="서귀포",     ppn=110_000, amenities=["수영장", "레스토랑"],                     rating=4.0),
        ],
        "싱가포르": [
            dict(name="하드록 호텔 센토사",      stars=4, location="센토사",     ppn=380_000, amenities=["수영장", "유니버설 접근", "워터파크"],    rating=4.5),
            dict(name="오아시아 호텔 노베나",    stars=4, location="노베나",     ppn=320_000, amenities=["루프탑풀", "피트니스", "레스토랑"],       rating=4.3),
            dict(name="이비스 벤쿨렌",           stars=3, location="부기스",     ppn=200_000, amenities=["교통 편의", "시내 접근"],                 rating=4.0),
            dict(name="이비스 싱가포르 노베나",  stars=3, location="노베나",     ppn=185_000, amenities=["피트니스", "레스토랑"],                   rating=4.1),
            dict(name="파스텔 싱가포르",         stars=2, location="차이나타운", ppn=85_000,  amenities=["공용 주방", "교통 접근"],                 rating=3.8),
        ],
        "발리": [
            dict(name="더블트리 리조트 꾸따",    stars=4, location="꾸따",        ppn=260_000, amenities=["수영장", "서핑 접근", "레스토랑"],        rating=4.4),
            dict(name="올라올라 비치 리조트",    stars=4, location="꾸따",        ppn=220_000, amenities=["수영장", "서핑 클래스", "레스토랑"],     rating=4.3),
            dict(name="에코 발리 클럽",          stars=3, location="꾸따",        ppn=160_000, amenities=["수영장", "액티비티 센터"],               rating=4.2),
            dict(name="리맥스 호텔 발리",        stars=3, location="스미냑",      ppn=130_000, amenities=["수영장", "레스토랑"],                    rating=4.1),
            dict(name="그린필드 발리",           stars=2, location="꾸따",        ppn=95_000,  amenities=["공용 주방", "서핑 접근"],                rating=3.8),
        ],
        "홍콩": [
            dict(name="케리 호텔 홍콩",          stars=5, location="훙함",        ppn=620_000, amenities=["수영장", "피트니스", "스파"],             rating=4.5),
            dict(name="노보텔 시티게이트",       stars=4, location="란타우",      ppn=310_000, amenities=["수영장", "디즈니랜드 접근"],             rating=4.3),
            dict(name="리갈 에어포트 호텔",      stars=4, location="란타우",      ppn=280_000, amenities=["수영장", "피트니스"],                    rating=4.2),
            dict(name="코즈웨이 베이 하우스",    stars=3, location="코즈웨이베이", ppn=240_000, amenities=["피트니스", "쇼핑몰 접근"],              rating=4.1),
            dict(name="링나 호텔",              stars=2, location="몽콕",         ppn=140_000, amenities=["교통 편의"],                             rating=3.9),
        ],
        "뉴욕": [
            dict(name="힐튼 뉴욕 미드타운",      stars=4, location="미드타운",    ppn=720_000, amenities=["피트니스", "레스토랑", "비즈니스센터"],   rating=4.3),
            dict(name="AC 호텔 타임스퀘어",      stars=4, location="타임스퀘어",  ppn=780_000, amenities=["피트니스", "루프탑", "교통 편의"],        rating=4.4),
            dict(name="파크 사우스 호텔",        stars=3, location="플랫아이언",  ppn=560_000, amenities=["피트니스", "레스토랑"],                   rating=4.2),
            dict(name="시티즌M 뉴욕",            stars=3, location="타임스퀘어",  ppn=580_000, amenities=["루프탑 바", "교통 편의"],                 rating=4.2),
            dict(name="HI 뉴욕 호스텔",          stars=1, location="어퍼웨스트",  ppn=280_000, amenities=["공용 주방", "투어 데스크"],               rating=3.9),
        ],
        "다낭": [
            dict(name="미아 리조트 다낭",        stars=4, location="미케 해변",   ppn=280_000, amenities=["수영장", "서핑 클럽", "워터스포츠"],     rating=4.5),
            dict(name="알로하 다낭 리조트",      stars=4, location="미케 해변",   ppn=250_000, amenities=["수영장", "서핑 레슨", "레스토랑"],       rating=4.4),
            dict(name="호이안 모나코 리조트",    stars=4, location="호이안",      ppn=290_000, amenities=["수영장", "자전거 투어", "레스토랑"],     rating=4.5),
            dict(name="그린 플라자 다낭",        stars=3, location="미케",         ppn=180_000, amenities=["수영장", "레저 시설"],                   rating=4.1),
            dict(name="그랜드 투리즈모 호텔",    stars=3, location="다낭 시내",    ppn=130_000, amenities=["피트니스", "레스토랑"],                   rating=4.0),
        ],
    },
    "맛집": {
        "도쿄": [
            dict(name="도쿄 스테이션 호텔",       stars=5, location="도쿄역",    ppn=520_000, amenities=["최고급 레스토랑", "명소 접근"],            rating=4.9),
            dict(name="더 로얄 파크 캔버스 긴자",  stars=4, location="긴자",     ppn=320_000, amenities=["미슐랭 거리 접근", "레스토랑"],            rating=4.7),
            dict(name="팜코트 아사쿠사",           stars=4, location="아사쿠사",  ppn=210_000, amenities=["식당 밀집", "전통 시장 접근"],             rating=4.3),
            dict(name="마이스테이즈 신주쿠",       stars=3, location="신주쿠",   ppn=142_000, amenities=["식당 밀집 지역", "야시장 접근"],           rating=4.4),
            dict(name="신주쿠 워싱턴 호텔",        stars=3, location="신주쿠",   ppn=160_000, amenities=["교통 편의", "이자카야 거리"],              rating=4.1),
        ],
        "오사카": [
            dict(name="크로스 호텔 도톤보리",    stars=4, location="도톤보리",   ppn=260_000, amenities=["맛집 밀집 지역", "레스토랑"],              rating=4.7),
            dict(name="힐튼 오사카",             stars=5, location="우메다",     ppn=390_000, amenities=["최고급 레스토랑", "스파"],                 rating=4.7),
            dict(name="호텔 몬테레이 라 수르",   stars=3, location="신사이바시", ppn=155_000, amenities=["쇼핑 거리", "식당 접근"],                  rating=4.4),
            dict(name="APA 호텔 난바 에키마에",  stars=3, location="난바",       ppn=120_000, amenities=["교통 편의", "야식 거리"],                  rating=4.2),
            dict(name="도레미 난바 도톤보리",    stars=3, location="난바",        ppn=105_000, amenities=["야식 거리", "맛집 접근"],                  rating=4.1),
        ],
        "방콕": [
            dict(name="차트리움 호텔 리버사이드", stars=5, location="차오프라야", ppn=450_000, amenities=["루프탑 레스토랑", "강변 뷰", "스파"],     rating=4.8),
            dict(name="홀리데이 인 방콕",         stars=4, location="실롬",       ppn=280_000, amenities=["레스토랑", "수쿰빗 접근"],                 rating=4.5),
            dict(name="마뇨파 방콕",              stars=4, location="방람푸",     ppn=195_000, amenities=["카오산 접근", "레스토랑"],                 rating=4.3),
            dict(name="이비스 방콕 수쿰빗",       stars=3, location="수쿰빗",     ppn=165_000, amenities=["야시장 접근", "식당 거리"],                rating=4.3),
            dict(name="원 방콕 스테이",           stars=3, location="야오와랏",   ppn=145_000, amenities=["차이나타운 접근", "식당 거리"],            rating=4.0),
        ],
        "싱가포르": [
            dict(name="스위소텔 더 스탬포드",    stars=5, location="시티홀",     ppn=620_000, amenities=["수영장", "스파", "레스토랑 8개"],          rating=4.6),
            dict(name="풀러턴 베이 호텔",        stars=5, location="마리나",     ppn=580_000, amenities=["수영장", "스파", "파인 다이닝"],           rating=4.6),
            dict(name="클락키 아쿠아 호텔",      stars=4, location="클락키",     ppn=340_000, amenities=["강변 뷰", "레스토랑 밀집 지역"],           rating=4.6),
            dict(name="아마라 싱가포르",         stars=4, location="텐저린",     ppn=280_000, amenities=["수영장", "레스토랑", "차이나타운 접근"],   rating=4.3),
            dict(name="호텔 81 차이나타운",      stars=3, location="차이나타운", ppn=155_000, amenities=["호커센터 접근", "교통 편의"],               rating=4.1),
        ],
        "발리": [
            dict(name="라 루나 리조트",          stars=5, location="길리",        ppn=480_000, amenities=["인피니티풀", "레스토랑", "다이빙"],       rating=4.7),
            dict(name="알라야 우부드",           stars=4, location="우부드",      ppn=310_000, amenities=["수영장", "레스토랑", "요리 클래스"],       rating=4.7),
            dict(name="세미냑 바이 크로마",      stars=4, location="세미냑",      ppn=350_000, amenities=["수영장", "레스토랑 거리 접근"],             rating=4.5),
            dict(name="아양가 우부드",           stars=4, location="우부드",      ppn=280_000, amenities=["수영장", "레스토랑", "쿠킹 클래스"],       rating=4.5),
            dict(name="로스메 구티",             stars=3, location="우부드",      ppn=160_000, amenities=["레스토랑", "로컬 투어"],                   rating=4.2),
        ],
        "홍콩": [
            dict(name="인터컨티넨탈 홍콩",       stars=5, location="침사추이",   ppn=780_000, amenities=["수영장", "스파", "미슐랭 레스토랑"],       rating=4.7),
            dict(name="랭함 플레이스 몽콕",      stars=5, location="몽콕",       ppn=480_000, amenities=["레스토랑", "딤섬 거리 접근"],               rating=4.7),
            dict(name="브렉퍼스트 호텔",         stars=4, location="미드레벨",   ppn=340_000, amenities=["레스토랑", "소호 접근"],                    rating=4.4),
            dict(name="노보텔 네이선 로드",      stars=3, location="침사추이",   ppn=230_000, amenities=["식당 거리", "교통 편의"],                   rating=4.3),
            dict(name="봄베이 드림스",           stars=3, location="완차이",     ppn=170_000, amenities=["식당 밀집", "교통 편의"],                   rating=4.0),
        ],
        "뉴욕": [
            dict(name="르 스크립토 뉴욕",        stars=4, location="첼시",        ppn=820_000, amenities=["맛집 밀집", "첼시마켓 접근"],              rating=4.5),
            dict(name="롤링 힐스 호텔",          stars=4, location="어퍼 이스트", ppn=680_000, amenities=["레스토랑", "센트럴파크 접근"],             rating=4.4),
            dict(name="NYY 스탠튼 호텔",         stars=3, location="로어 이스트", ppn=500_000, amenities=["식당 거리", "교통 편의"],                  rating=4.2),
            dict(name="위 호텔 소호",            stars=3, location="소호",         ppn=520_000, amenities=["식당 거리", "바 접근"],                    rating=4.2),
            dict(name="클린턴 홀 호텔",          stars=3, location="헬스 키친",    ppn=450_000, amenities=["식당 거리", "교통 편의"],                  rating=4.1),
        ],
        "다낭": [
            dict(name="포 시즌스 다낭",          stars=5, location="미케 해변",    ppn=1_200_000, amenities=["인피니티풀", "스파", "파인 다이닝"],    rating=4.9),
            dict(name="알라나 다낭 호텔",        stars=4, location="한 시장 인근", ppn=250_000, amenities=["레스토랑", "야시장 접근"],                rating=4.6),
            dict(name="다낭 미카사 호텔",        stars=4, location="한 시장",      ppn=220_000, amenities=["레스토랑", "시장 바로 앞"],               rating=4.5),
            dict(name="밀레니엄 리조트 다낭",    stars=3, location="미케 해변",    ppn=200_000, amenities=["레스토랑", "해변 접근"],                  rating=4.3),
            dict(name="데이즈 인 다낭",          stars=3, location="다낭 중심",    ppn=145_000, amenities=["레스토랑", "교통 편의"],                  rating=4.1),
        ],
    },
}


# ─────────────────────────────────────────────
# Google Places 기반 실제 호텔 조회
# ─────────────────────────────────────────────

# 목적지별 중심 좌표
_DEST_COORDS: dict[str, tuple[float, float]] = {
    "도쿄":     (35.6762,  139.6503),
    "오사카":   (34.6937,  135.5023),
    "방콕":     (13.7563,  100.5018),
    "파리":     (48.8566,    2.3522),
    "제주":     (33.4996,  126.5312),
    "싱가포르": ( 1.3521,  103.8198),
    "발리":     (-8.3405,  115.0920),
    "홍콩":     (22.3193,  114.1694),
    "뉴욕":     (40.7128,  -74.0060),
    "다낭":     (16.0544,  108.2022),
}

# 목적지 × 별점별 1박 기준가 (KRW)
_DEST_BASE_PRICE: dict[str, dict[int, int]] = {
    "도쿄":     {5: 480_000, 4: 240_000, 3: 130_000, 2: 75_000},
    "오사카":   {5: 390_000, 4: 200_000, 3: 110_000, 2: 65_000},
    "방콕":     {5: 420_000, 4: 180_000, 3: 100_000, 2: 55_000},
    "파리":     {5: 850_000, 4: 450_000, 3: 270_000, 2: 160_000},
    "제주":     {5: 420_000, 4: 210_000, 3: 120_000, 2: 70_000},
    "싱가포르": {5: 750_000, 4: 370_000, 3: 200_000, 2: 110_000},
    "발리":     {5: 550_000, 4: 270_000, 3: 140_000, 2: 80_000},
    "홍콩":     {5: 850_000, 4: 380_000, 3: 210_000, 2: 120_000},
    "뉴욕":     {5: 2_000_000, 4: 750_000, 3: 480_000, 2: 300_000},
    "다낭":     {5: 550_000, 4: 260_000, 3: 140_000, 2: 80_000},
}
_DEFAULT_BASE_PRICE: dict[int, int] = {5: 500_000, 4: 250_000, 3: 130_000, 2: 70_000}

# 별점별 기본 어메니티
_AMENITIES_BY_STARS: dict[int, list[str]] = {
    5: ["수영장", "스파", "피트니스", "레스토랑", "컨시어지"],
    4: ["피트니스", "레스토랑", "룸서비스"],
    3: ["레스토랑", "조식 포함"],
    2: ["조식 포함", "기본 시설"],
}


def _estimate_stars(rating: float) -> int:
    if rating >= 4.5: return 5
    if rating >= 4.1: return 4
    if rating >= 3.7: return 3
    return 2


def _estimate_price(destination: str, stars: int, review_count: int) -> int:
    base = _DEST_BASE_PRICE.get(destination, _DEFAULT_BASE_PRICE)[stars]
    # 리뷰 많을수록 유명 = 약간 높은 가격 (±20%)
    popularity = min(review_count / 5000, 1.0)
    return int(base * (1.0 + popularity * 0.2))


def _shorten_address(vicinity: str) -> str:
    """'6-chōme-6-2 Nishishinjuku, Shinjuku City' → 'Shinjuku City' 형태로 단축"""
    parts = [p.strip() for p in vicinity.split(",")]
    # 숫자로 시작하지 않고 ASCII 비중이 높은 파트를 뒤에서부터 선택
    for part in reversed(parts):
        if not part:
            continue
        ascii_ratio = sum(1 for c in part if ord(c) < 128) / len(part)
        starts_with_digit = part[0].isdigit()
        if ascii_ratio >= 0.6 and not starts_with_digit:
            return part
    return parts[-1] if parts else vicinity


def _fetch_hotels_places(destination: str, nights: int,
                          budget_per_night: int) -> list[Hotel]:
    api_key = os.environ.get("GOOGLE_PLACES_KEY", "").strip()
    coords  = _DEST_COORDS.get(destination)
    if not api_key or not coords:
        return []

    params = {
        "location": f"{coords[0]},{coords[1]}",
        "radius":   "12000",
        "type":     "lodging",
        "language": "ko",
        "rankby":   "prominence",
        "key":      api_key,
    }
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        if data.get("status") not in ("OK", "ZERO_RESULTS"):
            return []
        results = data.get("results", [])
    except Exception as exc:
        print(f"  ⚠️  Places 호텔 API 오류: {exc}")
        return []

    # 평점 3.8+ 필터 → 리뷰수 가중 정렬
    filtered = [
        r for r in results
        if r.get("rating", 0) >= 3.8 and r.get("user_ratings_total", 0) >= 50
    ]
    filtered.sort(key=lambda r: (r.get("rating", 0) * 0.6 +
                                  min(r.get("user_ratings_total", 0) / 10000, 1) * 0.4),
                  reverse=True)

    hotels: list[Hotel] = []
    for r in filtered[:8]:
        rating   = r.get("rating", 4.0)
        reviews  = r.get("user_ratings_total", 0)
        stars    = _estimate_stars(rating)
        ppn      = _estimate_price(destination, stars, reviews)
        vicinity = r.get("vicinity", destination)

        hotels.append(Hotel(
            name            = r["name"],
            stars           = stars,
            location        = _shorten_address(vicinity),
            price_per_night = ppn,
            amenities       = _AMENITIES_BY_STARS[stars],
            rating          = rating,
            total_price     = ppn * nights,
        ))

    return hotels


# ─────────────────────────────────────────────
# Mock 폴백 검색
# ─────────────────────────────────────────────

def _search_mock(destination: str, nights: int,
                 budget_per_night: int, style: str) -> list[Hotel]:
    style_db = _HOTEL_DB.get(style, _HOTEL_DB["휴양"])
    raw = style_db.get(destination) or [
        dict(name=f"{destination} 럭셔리 호텔",  stars=5, location=f"{destination} 중심가", ppn=450_000, amenities=["수영장", "스파", "레스토랑"], rating=4.8),
        dict(name=f"{destination} 비즈니스 호텔", stars=4, location=f"{destination} 시내",   ppn=220_000, amenities=["피트니스", "레스토랑"],       rating=4.4),
        dict(name=f"{destination} 이코노미 호텔", stars=3, location=f"{destination} 외곽",   ppn=115_000, amenities=["기본 시설"],                  rating=4.0),
    ]
    hotels = [
        Hotel(name=r["name"], stars=r["stars"], location=r["location"],
              price_per_night=r["ppn"], amenities=r["amenities"],
              rating=r["rating"], total_price=r["ppn"] * nights)
        for r in raw
    ]
    in_budget = [h for h in hotels if h.price_per_night <= budget_per_night]
    return (in_budget if in_budget else hotels)[:5]


# ─────────────────────────────────────────────
# 검색·출력·비용 계산
# ─────────────────────────────────────────────

def search_hotels(destination: str, nights: int,
                  budget_per_night: int, style: str) -> list[Hotel]:
    hotels = _fetch_hotels_places(destination, nights, budget_per_night)
    if len(hotels) >= 3:
        # 예산 내 우선 → 전체로 폴백
        in_budget = [h for h in hotels if h.price_per_night <= budget_per_night]
        return (in_budget if in_budget else hotels)[:5]
    return _search_mock(destination, nights, budget_per_night, style)


def display_hotels(hotels: list[Hotel], nights: int, ppn_budget: int) -> None:
    api_key = os.environ.get("GOOGLE_PLACES_KEY", "")
    src     = "Google Places 실시간" if api_key else "Mock 데이터"
    print("\n" + "━" * 62)
    print(f"  🏨  호텔 추천 ({src})")
    print("━" * 62)
    for i, h in enumerate(hotels, 1):
        tag   = "✅ 예산 내" if h.price_per_night <= ppn_budget else "⚠️ 예산 초과"
        stars = "★" * h.stars + "☆" * (5 - h.stars)
        print(f"\n  [{i}] {stars}  {h.name}  {tag}")
        print(f"      📍 {h.location}  |  평점 {h.rating}/5.0")
        print(f"      💰 1박 {h.price_per_night:,}원  →  {nights}박 합계 {h.total_price:,}원")
        print(f"      🛎  {' · '.join(h.amenities)}")


def calculate_costs(flight_price: int, hotel: Hotel,
                    nights: int, passengers: int, budget: int) -> dict:
    misc  = passengers * nights * 80_000
    total = flight_price + hotel.total_price + misc
    return dict(
        flight=flight_price, hotel=hotel.total_price,
        misc=misc, total=total, budget=budget,
        over_budget=total > budget,
        difference=abs(total - budget),
    )


def run(destination: str, nights: int,
        budget_per_night: int, style: str) -> list[Hotel]:
    return search_hotels(destination, nights, budget_per_night, style)
