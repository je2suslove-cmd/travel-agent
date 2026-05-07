"""
일정 생성 에이전트
여행지별 스타일 맞춤 일정 출력 + 날씨·실제 장소 데이터 통합
"""
from __future__ import annotations

from datetime import datetime, timedelta

from flight_agent import Flight
from hotel_agent import Hotel
from places_agent import Attraction, Restaurant, _PRICE_LEVEL
from weather_agent import WeatherDay

from destinations import _DEST_DATA, _GENERIC_DEST


# ─────────────────────────────────────────────
# 일정 생성
# ─────────────────────────────────────────────

def _build_generic_days(destination: str, style: str, nights: int) -> list[dict]:
    """알려지지 않은 여행지 기본 일정 생성"""
    focus_map = {
        "휴양":    "리조트와 스파 이용",
        "액티비티": "현지 투어와 체험 프로그램",
        "맛집":    "현지 레스토랑과 시장 탐방",
    }
    focus = focus_map.get(style, "관광명소 탐방")
    days: list[dict] = []
    for i in range(nights + 1):
        if i == 0:
            days.append({
                "title":     "도착 & 첫인상",
                "morning":   "공항 도착 후 환전, 호텔 체크인 및 주변 탐색",
                "afternoon": f"{destination} 중심가 가볍게 탐방",
                "evening":   "호텔 인근 현지 레스토랑 저녁",
                "night":     "숙소 휴식",
                "cost":      "교통비 + 저녁 식사",
            })
        elif i == nights:
            days.append({
                "title":     "마지막 날 & 귀국",
                "morning":   "호텔 체크아웃 전 마지막 산책",
                "afternoon": "기념품 구매 후 공항 이동",
                "evening":   "귀국 탑승",
                "night":     "기내",
                "cost":      "기념품 쇼핑",
            })
        else:
            days.append({
                "title":     f"{i + 1}일차 — {focus}",
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
    weather_days: list[WeatherDay] | None = None,
    restaurants: list[Restaurant] | None = None,
    attractions: list[Attraction] | None = None,
) -> None:
    dest       = info["destination"]
    style      = info["style"]
    nights     = info["nights"]
    total_days = nights + 1
    passengers = info["passengers"]

    dest_info  = _DEST_DATA.get(dest, _GENERIC_DEST)
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
                "title":     f"자유 여행 Day {len(days) + 1}",
                "morning":   "원하는 명소 자유 탐방",
                "afternoon": "카페 or 쇼핑몰 여유",
                "evening":   "현지 레스토랑 저녁",
                "night":     "야경 포인트 방문",
                "cost":      "자유 지출",
            })
    else:
        days = raw_days

    start_dt = datetime.strptime(info["start_date"], "%Y-%m-%d")
    tips:    list[str] = style_data.get("tips", [])
    packing: list[str] = style_data.get("packing", [])

    # 날씨 조회 dict (날짜 → WeatherDay)
    weather_map: dict[str, WeatherDay] = {}
    if weather_days:
        weather_map = {w.date: w for w in weather_days}

    sep = "━" * 62

    print("\n" + sep)
    print(f"  📅  {dest} {nights}박 {total_days}일 {style} 여행 일정")
    print(sep)

    # 기본 요약
    print(f"\n  ✈️  {flight.airline} {flight.flight_no}  |  {flight.departure} → {flight.arrival}")
    print(f"      출발 {flight.dep_time}  →  도착 {flight.arr_time}  (소요 {flight.duration})")
    print(f"  🏨  {'★' * hotel.stars}  {hotel.name}  ({hotel.location})")
    print(f"  💰  총 예상 비용: {costs['total']:,}원  (예산: {costs['budget']:,}원)")
    if costs["over_budget"]:
        print(f"  ⚠️  예산 {costs['difference']:,}원 초과 — 숙박 등급 조정을 고려해보세요.")
    else:
        print(f"  ✅  예산 {costs['difference']:,}원 여유")

    # Day별 일정
    print(f"\n{'─' * 62}")
    print("  [ 상세 일정 ]")
    print(f"{'─' * 62}")

    for i, day in enumerate(days):
        date_str = (start_dt + timedelta(days=i)).strftime("%m월 %d일")
        date_key = (start_dt + timedelta(days=i)).strftime("%Y-%m-%d")

        weather_tag = ""
        if date_key in weather_map:
            w = weather_map[date_key]
            weather_tag = f"  🌤 {w.description} {w.temp_max:.0f}°/{w.temp_min:.0f}°C"

        print(f"\n  ▶  Day {i + 1}  ({date_str}){weather_tag}  —  {day['title']}")
        print(f"     🌅 오전   {day['morning']}")
        print(f"     ☀️ 오후   {day['afternoon']}")
        print(f"     🌆 저녁   {day['evening']}")
        print(f"     🌙 야간   {day['night']}")
        print(f"     💸 비용   {day['cost']}")

    # 현지 꿀팁
    if tips:
        print(f"\n{'─' * 62}")
        print("  [ 현지 실전 꿀팁 ]")
        print(f"{'─' * 62}")
        for tip in tips:
            print(f"  ✔  {tip}")

    # 현지 기본 정보
    print(f"\n{'─' * 62}")
    print("  [ 현지 기본 정보 ]")
    print(f"{'─' * 62}")
    print(f"  💱 통화      {dest_info['currency']}")
    print(f"  🏧 환전 팁   {dest_info['exchange_tip']}")
    print(f"  🚇 교통      {dest_info['transport']}")
    print(f"  🔌 플러그    {dest_info['plug']}")
    print(f"  🕐 시차      {dest_info['시차']}")
    print(f"  ☀️ 날씨 팁   {dest_info['계절_팁']}")

    # 짐 체크리스트
    if packing:
        print(f"\n{'─' * 62}")
        print("  [ 짐 챙기기 체크리스트 ]")
        print(f"{'─' * 62}")
        for item in packing:
            print(f"  ☐  {item}")
        print(f"  ☐  여권 (유효기간 6개월 이상)")
        print(f"  ☐  여행자 보험 가입 확인")
        print(f"  ☐  현지 비상 연락처 메모")

    # 예상 비용 내역
    print(f"\n{'─' * 62}")
    print("  [ 예상 비용 내역 ]")
    print(f"{'─' * 62}")
    print(f"  ✈️  항공권 ({passengers}명)       {costs['flight']:>12,}원")
    print(f"  🏨  숙박 ({nights}박)            {costs['hotel']:>12,}원")
    print(f"  🍽️  식비·교통·관광 (추정)    {costs['misc']:>12,}원")
    print(f"  {'─' * 46}")
    print(f"  💳  총 예상 비용             {costs['total']:>12,}원")
    print(f"  📦  설정 예산                {costs['budget']:>12,}원")

    # Google Places 실제 데이터
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


def get_data(
    info: dict,
    flight: Flight,
    hotel: Hotel,
    costs: dict,
    weather_days: list[WeatherDay] | None = None,
    restaurants: list[Restaurant] | None = None,
    attractions: list[Attraction] | None = None,
) -> dict:
    """웹 UI용 — 출력 대신 구조화된 dict 반환"""
    dest       = info["destination"]
    style      = info["style"]
    nights     = info["nights"]
    total_days = nights + 1

    dest_info  = _DEST_DATA.get(dest, _GENERIC_DEST)
    style_data = dest_info.get(style, dest_info.get("휴양", {"days": [], "tips": [], "packing": []}))

    raw_days: list[dict] = style_data.get("days", [])
    if not raw_days:
        raw_days = _build_generic_days(dest, style, nights)

    if len(raw_days) > total_days:
        days = raw_days[:total_days]
    elif len(raw_days) < total_days:
        days = list(raw_days)
        for _ in range(total_days - len(raw_days)):
            days.append({
                "title":     f"자유 여행 Day {len(days) + 1}",
                "morning":   "원하는 명소 자유 탐방",
                "afternoon": "카페 or 쇼핑몰 여유",
                "evening":   "현지 레스토랑 저녁",
                "night":     "야경 포인트 방문",
                "cost":      "자유 지출",
            })
    else:
        days = raw_days

    start_dt    = datetime.strptime(info["start_date"], "%Y-%m-%d")
    weather_map = {w.date: w for w in (weather_days or [])}

    enriched: list[dict] = []
    for i, day in enumerate(days):
        date_dt  = start_dt + timedelta(days=i)
        date_key = date_dt.strftime("%Y-%m-%d")
        w        = weather_map.get(date_key)
        enriched.append({
            "day_num":   i + 1,
            "date":      date_dt.strftime("%m월 %d일"),
            "date_full": date_key,
            "title":     day["title"],
            "morning":   day["morning"],
            "afternoon": day["afternoon"],
            "evening":   day["evening"],
            "night":     day["night"],
            "cost":      day["cost"],
            "weather":   w,
        })

    return {
        "dest":        dest,
        "style":       style,
        "nights":      nights,
        "total_days":  total_days,
        "days":        enriched,
        "tips":        style_data.get("tips", []),
        "packing":     style_data.get("packing", []),
        "dest_info":   dest_info,
        "restaurants": restaurants or [],
        "attractions": attractions or [],
    }


def run(
    info: dict,
    flight: Flight,
    hotel: Hotel,
    costs: dict,
    weather_days: list[WeatherDay] | None = None,
    restaurants: list[Restaurant] | None = None,
    attractions: list[Attraction] | None = None,
) -> None:
    generate_itinerary(info, flight, hotel, costs, weather_days, restaurants, attractions)
