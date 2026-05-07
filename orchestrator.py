"""
총괄 오케스트레이터
사용자 입력 수집 후 각 에이전트를 순서대로 호출하고 결과를 취합합니다.

실행: python3 orchestrator.py
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

import flight_agent
import hotel_agent
import places_agent
import planner_agent
import weather_agent


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
# 메인 — 에이전트 순서대로 호출
# ─────────────────────────────────────────────

def main() -> None:
    info = get_user_input()

    # ── 1. 항공편 에이전트
    print("\n🔍 [항공편 에이전트] 항공편을 검색하고 있습니다...")
    flights = flight_agent.run(info["origin"], info["destination"], info["passengers"])
    flight_agent.display_flights(flights, info["passengers"])
    selected_flight = flights[0]
    print(f"\n  → 최저가 항공편 자동 선택: {selected_flight.airline} {selected_flight.flight_no}  ({selected_flight.price:,}원)")

    # ── 2. 호텔 에이전트
    remaining_budget = info["budget"] - selected_flight.price
    ppn_budget = max(int(remaining_budget * 0.40 / info["nights"]), 50_000)

    print("\n🔍 [호텔 에이전트] 호텔을 검색하고 있습니다...")
    hotels = hotel_agent.run(info["destination"], info["nights"], ppn_budget, info["style"])
    hotel_agent.display_hotels(hotels, info["nights"], ppn_budget)
    selected_hotel = max(hotels, key=lambda h: (h.price_per_night <= ppn_budget, h.rating))
    print(f"\n  → 추천 호텔 선택: {selected_hotel.name}  (평점 {selected_hotel.rating}/5.0)")

    costs = hotel_agent.calculate_costs(
        selected_flight.price, selected_hotel,
        info["nights"], info["passengers"], info["budget"],
    )

    # ── 3. 날씨 에이전트
    print("\n🌤 [날씨 에이전트] 날씨 예보를 가져오고 있습니다...")
    weather_days, clothing = weather_agent.run(
        info["destination"], info["start_date"], info["nights"],
    )
    weather_agent.display_weather(weather_days, clothing)

    # ── 4. 장소 에이전트 (Google Places API 키 있을 때만)
    places_key = os.environ.get("GOOGLE_PLACES_KEY", "")
    restaurants: list = []
    attractions: list = []

    if places_key:
        print("\n🔍 [장소 에이전트] Google Places API로 음식점·관광지를 검색 중...")
        restaurants, attractions = places_agent.run(info["destination"], places_key)
        places_agent.display_restaurants(restaurants)
        places_agent.display_attractions(attractions)
    else:
        print("\n  ℹ️  [장소 에이전트] GOOGLE_PLACES_KEY 미설정 — 실시간 장소 검색 생략")
        print("     (export GOOGLE_PLACES_KEY=your_key 설정 시 실제 데이터 사용)")

    # ── 5. 일정 에이전트
    print("\n✍️  [일정 에이전트] 맞춤 여행 일정을 생성하고 있습니다...\n")
    planner_agent.run(
        info, selected_flight, selected_hotel, costs,
        weather_days=weather_days,
        restaurants=restaurants,
        attractions=attractions,
    )

    print("\n" + "=" * 62)
    print("  🎉  일정 생성 완료!  즐거운 여행 되세요! ✈️")
    print("=" * 62 + "\n")


if __name__ == "__main__":
    main()
