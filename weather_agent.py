"""
날씨·옷차림 에이전트
Open-Meteo 무료 API 사용 — API 키 불필요, 최대 16일 예보 지원
"""
from __future__ import annotations

import json
import threading
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta


# ─────────────────────────────────────────────
# 인메모리 캐시  (TTL: 3600초)
# ─────────────────────────────────────────────

_CACHE: dict[tuple, tuple[float, list]] = {}
_CACHE_LOCK = threading.Lock()
_CACHE_TTL  = 3600.0


def _cache_get(key: tuple) -> list | None:
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if entry and (datetime.now().timestamp() - entry[0]) < _CACHE_TTL:
            return entry[1]
    return None


def _cache_set(key: tuple, value: list) -> None:
    with _CACHE_LOCK:
        _CACHE[key] = (datetime.now().timestamp(), value)


# ─────────────────────────────────────────────
# 데이터 모델
# ─────────────────────────────────────────────

@dataclass
class WeatherDay:
    date: str
    temp_max: float
    temp_min: float
    precipitation: float   # mm (예보 시 추정값, 아카이브 시 실측값)
    description: str
    is_archive: bool = False  # True = 전년 동기 실측값


# WMO 날씨 코드 → 한국어 설명
_WMO: dict[int, str] = {
    0: "맑음",
    1: "대체로 맑음", 2: "구름 조금", 3: "흐림",
    45: "안개", 48: "서리 안개",
    51: "가벼운 이슬비", 53: "이슬비", 55: "강한 이슬비",
    56: "어는 이슬비", 57: "강한 어는 이슬비",
    61: "가벼운 비", 63: "비", 65: "강한 비",
    66: "어는 비", 67: "강한 어는 비",
    71: "가벼운 눈", 73: "눈", 75: "강한 눈", 77: "싸락눈",
    80: "소나기", 81: "강한 소나기", 82: "폭우",
    85: "눈 소나기", 86: "강한 눈 소나기",
    95: "뇌우", 96: "뇌우+우박", 99: "강한 뇌우+우박",
}


# ─────────────────────────────────────────────
# API 호출
# ─────────────────────────────────────────────

def _geocode(destination: str) -> tuple[float, float] | None:
    """여행지 좌표 조회 (Open-Meteo Geocoding — 무료)"""
    url = "https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode(
        {"name": destination, "count": 1, "language": "ko"}
    )
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read())
        results = data.get("results", [])
        if not results:
            return None
        return results[0]["latitude"], results[0]["longitude"]
    except Exception:
        return None


def get_forecast(destination: str, start_date: str, nights: int) -> list[WeatherDay]:
    """
    Open-Meteo 날씨 조회.
    - 16일 이내: 실시간 예보 API
    - 16일 초과: 전년도 같은 기간 아카이브 API (기후 경향 참고값)
    - 결과는 1시간 인메모리 캐시
    """
    cache_key = (destination, start_date, nights)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    start_dt   = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt     = start_dt + timedelta(days=nights)
    days_until = (start_dt - datetime.today()).days
    is_archive = days_until > 15

    coords = _geocode(destination)
    if not coords:
        return []
    lat, lon = coords

    if is_archive:
        try:
            ref_start = start_dt.replace(year=start_dt.year - 1)
            ref_end   = end_dt.replace(year=end_dt.year - 1)
        except ValueError:          # 윤년 2/29 예외
            ref_start = start_dt.replace(year=start_dt.year - 2)
            ref_end   = end_dt.replace(year=end_dt.year - 2)
        params = {
            "latitude":   lat,
            "longitude":  lon,
            "daily":      "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
            "timezone":   "auto",
            "start_date": ref_start.strftime("%Y-%m-%d"),
            "end_date":   ref_end.strftime("%Y-%m-%d"),
        }
        base_url = "https://archive-api.open-meteo.com/v1/archive"
    else:
        params = {
            "latitude":   lat,
            "longitude":  lon,
            "daily":      "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
            "timezone":   "auto",
            "start_date": start_date,
            "end_date":   end_dt.strftime("%Y-%m-%d"),
        }
        base_url = "https://api.open-meteo.com/v1/forecast"

    url = base_url + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read())
    except Exception as exc:
        print(f"  ⚠️  날씨 API 요청 실패: {exc}")
        return []

    daily  = data.get("daily", {})
    t_max  = daily.get("temperature_2m_max", [])
    t_min  = daily.get("temperature_2m_min", [])
    precip = daily.get("precipitation_sum", [])
    codes  = daily.get("weathercode", [])

    result: list[WeatherDay] = []
    for i in range(len(t_max)):
        code         = int(codes[i]) if i < len(codes) else 0
        actual_date  = (start_dt + timedelta(days=i)).strftime("%Y-%m-%d")
        result.append(WeatherDay(
            date          = actual_date,
            temp_max      = t_max[i]  if i < len(t_max)  else 0.0,
            temp_min      = t_min[i]  if i < len(t_min)  else 0.0,
            precipitation = precip[i] if i < len(precip) else 0.0,
            description   = _WMO.get(code, f"날씨({code})"),
            is_archive    = is_archive,
        ))
    _cache_set(cache_key, result)
    return result


# ─────────────────────────────────────────────
# 옷차림 추천
# ─────────────────────────────────────────────

def get_clothing(weather_days: list[WeatherDay]) -> list[str]:
    if not weather_days:
        return []

    avg_max = sum(d.temp_max for d in weather_days) / len(weather_days)
    avg_min = sum(d.temp_min for d in weather_days) / len(weather_days)
    has_rain    = any(d.precipitation > 1.0 for d in weather_days)
    has_thunder = any("뇌우" in d.description for d in weather_days)
    has_snow    = any("눈" in d.description for d in weather_days)

    clothes: list[str] = []
    if avg_max >= 30:
        clothes += ["민소매 or 반팔", "반바지 or 얇은 원피스", "샌들", "선크림 SPF50+ 필수", "모자·선글라스"]
    elif avg_max >= 23:
        clothes += ["반팔 티셔츠", "얇은 가디건 (저녁용)", "긴 바지 or 반바지", "운동화", "선크림"]
    elif avg_max >= 15:
        clothes += ["긴팔 셔츠", "가디건 or 후드집업", "청바지", "운동화", "얇은 재킷 (아침·저녁)"]
    elif avg_max >= 5:
        clothes += ["두꺼운 니트 or 스웨터", "코트 or 두꺼운 재킷", "두꺼운 바지", "부츠 or 워커", "목도리"]
    else:
        clothes += ["패딩 점퍼", "기모 레깅스 or 두꺼운 바지", "목도리·장갑·모자", "방한화", "핫팩"]

    if avg_max - avg_min > 12:
        clothes.append("일교차 큼 — 겉옷 반드시 지참")
    if has_rain:
        clothes.append("우산 or 우비 (비 예보 있음)")
    if has_snow:
        clothes.append("방수 장갑·방한 부츠 (눈 예보 있음)")
    if has_thunder:
        clothes.append("⚠️ 뇌우 예보 — 야외 일정 사전 확인 권장")

    return clothes


# ─────────────────────────────────────────────
# 출력
# ─────────────────────────────────────────────

def display_weather(weather_days: list[WeatherDay], clothing: list[str]) -> None:
    print("\n" + "━" * 62)
    print("  🌤️  여행 기간 날씨 예보  (Open-Meteo · 무료 API)")
    print("━" * 62)

    if not weather_days:
        print("  ℹ️  날씨 정보 없음 — 출발일이 16일 이상 남았거나 네트워크 오류")
    else:
        for d in weather_days:
            rain_str = f"  🌧 {d.precipitation:.1f}mm" if d.precipitation > 0.5 else ""
            print(f"  {d.date}  {d.description:<14}  ↑{d.temp_max:.0f}°C / ↓{d.temp_min:.0f}°C{rain_str}")

    if clothing:
        print(f"\n{'─' * 62}")
        print("  [ 옷차림 추천 ]")
        print(f"{'─' * 62}")
        for item in clothing:
            print(f"  👕 {item}")


def run(destination: str, start_date: str, nights: int) -> tuple[list[WeatherDay], list[str]]:
    weather_days = get_forecast(destination, start_date, nights)
    clothing     = get_clothing(weather_days)
    return weather_days, clothing
