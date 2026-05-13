"""
음식점·관광지 에이전트
Google Places Text Search API (Legacy) 사용
환경변수 GOOGLE_PLACES_KEY 필요
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass


# ─────────────────────────────────────────────
# 데이터 모델
# ─────────────────────────────────────────────

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


_PRICE_LEVEL: dict[int, str] = {
    -1: "", 0: "무료", 1: "₩", 2: "₩₩", 3: "₩₩₩", 4: "₩₩₩₩",
}


# 여행지별 중심 좌표 (위치 바이어스용)
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
_SEARCH_RADIUS = 15_000  # 15km


def _brand_key(name: str) -> str:
    """체인점 중복 제거용 브랜드 키: 괄호·지점명·지역명 제거 후 정규화"""
    key = re.sub(r'[\(（][^)）]*[\)）]', '', name)          # (구 나베조) 등 괄호 제거
    key = re.sub(r'\s+\S*(?:점|店|支店|branch)\S*', '', key)  # 시부야점 등 지점명 제거
    key = re.sub(r'(?<=[A-Za-z])\s+[\w가-힣ぁ-んァ-ン]+\s*$', '', key)  # 영문 뒤 지역어 제거
    key = re.sub(r'[^\w가-힣ぁ-んァ-ン]', '', key).lower()
    return key or re.sub(r'[^\w가-힣ぁ-んァ-ン]', '', name).lower()


# ─────────────────────────────────────────────
# API 호출  (실제 API 교체 지점 — Google Places)
# ─────────────────────────────────────────────

def _places_search(query: str, api_key: str, place_type: str = "",
                   location: tuple[float, float] | None = None) -> list[dict]:
    """Google Places Text Search API 호출"""
    params: dict[str, str] = {"query": query, "key": api_key, "language": "ko"}
    if place_type:
        params["type"] = place_type
    if location:
        params["location"] = f"{location[0]},{location[1]}"
        params["radius"]   = str(_SEARCH_RADIUS)
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


def search_restaurants(destination: str, api_key: str) -> list[Restaurant]:
    """여행지 음식점 검색 — 평점 높은 순, 동일 브랜드 중복 제거"""
    coords = _DEST_COORDS.get(destination)
    results = _places_search("맛집 레스토랑", api_key, "restaurant", location=coords)
    items = sorted(
        [
            Restaurant(
                name=r["name"],
                address=r.get("formatted_address", r.get("vicinity", "주소 정보 없음")),
                rating=r.get("rating", 0.0),
                review_count=r.get("user_ratings_total", 0),
                price_level=r.get("price_level", -1),
                place_id=r.get("place_id", ""),
            )
            for r in results if r.get("name")
        ],
        key=lambda x: x.rating, reverse=True,
    )
    seen: set[str] = set()
    deduped: list[Restaurant] = []
    for item in items:
        key = _brand_key(item.name)
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped[:10]


def search_attractions(destination: str, api_key: str) -> list[Attraction]:
    """여행지 관광지 검색 — 평점 높은 순, 동일 명소 중복 제거"""
    coords = _DEST_COORDS.get(destination)
    results = _places_search("관광지 명소", api_key, "tourist_attraction", location=coords)
    items = sorted(
        [
            Attraction(
                name=r["name"],
                address=r.get("formatted_address", r.get("vicinity", "주소 정보 없음")),
                rating=r.get("rating", 0.0),
                review_count=r.get("user_ratings_total", 0),
                place_id=r.get("place_id", ""),
            )
            for r in results if r.get("name")
        ],
        key=lambda x: x.rating, reverse=True,
    )
    seen: set[str] = set()
    deduped: list[Attraction] = []
    for item in items:
        key = _brand_key(item.name)
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped[:10]


# ─────────────────────────────────────────────
# 출력
# ─────────────────────────────────────────────

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


def run(destination: str, api_key: str = "") -> tuple[list[Restaurant], list[Attraction]]:
    if not api_key:
        return [], []
    restaurants = search_restaurants(destination, api_key)
    attractions  = search_attractions(destination, api_key)
    return restaurants, attractions
