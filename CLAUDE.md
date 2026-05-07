# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 실행 방법

```bash
# 웹 UI (Flask)
python3 app.py          # http://localhost:5000

# CLI (터미널 대화형 입력)
python3 orchestrator.py

# 환경변수 (선택)
export GOOGLE_PLACES_KEY=your_key   # 없으면 음식점·관광지 섹션 비어있음
```

의존성 설치:
```bash
pip install -r requirements.txt     # anthropic>=0.40.0, flask>=3.0.0
```

## 아키텍처

두 가지 실행 경로가 동일한 에이전트 파이프라인을 공유한다.

```
웹(app.py) ──┐
             ├──▶ flight_agent → hotel_agent → weather_agent → places_agent → planner_agent
CLI(orchestrator.py) ──┘
```

### 에이전트별 역할

| 파일 | 역할 | 외부 의존 |
|------|------|-----------|
| `flight_agent.py` | 출발지·목적지·인원으로 항공편 검색, 최저가 정렬 | Mock (`_FLIGHT_DB`) — Amadeus/Skyscanner 교체 가능 |
| `hotel_agent.py` | 여행지·스타일·1박 예산으로 호텔 검색 + 비용 계산 | Mock (`_HOTEL_DB`) — 스타일(휴양/액티비티/맛집)별 |
| `weather_agent.py` | 출발일 기준 16일 이내 날씨 예보 + 옷차림 추천 | Open-Meteo 무료 API (키 불필요) |
| `places_agent.py` | 음식점·관광지 실시간 검색 | Google Places Text Search API (`GOOGLE_PLACES_KEY`) |
| `planner_agent.py` | 여행지·스타일별 상세 일정 조합, `generate_itinerary()`(CLI 출력) / `get_data()`(웹 반환) | `travel_agent.py`의 `_DEST_DATA` |
| `travel_agent.py` | 10개 여행지 × 3개 스타일 × 4일 분량 일정 콘텐츠 저장소 | 없음 (데이터 모듈) |

### 핵심 데이터 흐름

1. **항공권 선택**: `flights[0]` (최저가 자동 선택)
2. **호텔 예산 계산**: `(총예산 - 항공료) × 0.40 / 숙박일수` → `ppn_budget`
3. **호텔 선택**: `max(hotels, key=lambda h: (h.price_per_night <= ppn_budget, h.rating))` — 예산 내에서 최고 평점
4. **일정 콘텐츠**: `planner_agent`가 `travel_agent._DEST_DATA[목적지][스타일]["days"]` 로드, 숙박 일수에 맞게 잘라내거나 "자유 여행" 일차 자동 추가

### 두 출력 모드의 차이

- `planner_agent.generate_itinerary()` — CLI 전용, `print()`로 직접 출력
- `planner_agent.get_data()` — Flask 전용, 구조화된 `dict` 반환 (Jinja2 템플릿에 전달)

### 여행지 콘텐츠 확장

`travel_agent.py`의 `_DEST_DATA`가 유일한 여행지 콘텐츠 소스다. 지원 목적지는 도쿄·오사카·방콕·파리·제주·싱가포르·발리·홍콩·뉴욕·다낭 10곳. 새 여행지 추가 시 이 딕셔너리에만 추가하면 웹/CLI 양쪽에 적용된다. 미지원 여행지는 `_GENERIC_DEST`가 기본 일정으로 대체된다.

### 실제 API 교체 지점

- **항공편**: `flight_agent.py`의 `search_flights()` 내부 `_FLIGHT_DB` 조회 부분 → Amadeus/Skyscanner SDK로 교체
- **호텔**: `hotel_agent.py`의 `search_hotels()` 내부 `_HOTEL_DB` 조회 부분 → Booking.com/Expedia API로 교체
- **음식점·관광지**: `places_agent.py`는 이미 실제 API 연동 (`GOOGLE_PLACES_KEY` 필요)

### Flask 앱 특이사항

- Jinja2 커스텀 필터 `urlquote` 등록 (`app.py`) — 호텔 카드의 Booking.com 검색 링크 URL 인코딩에 사용
- `has_places` 플래그를 템플릿에 전달해 API 키 유무에 따라 안내 메시지를 분기 처리
- `GOOGLE_PLACES_KEY` 환경변수는 `.strip()` 처리 후 전달 (공백 포함 시 API 오류 방지)

## 앞으로 추가할 기능

- [ ] 실제 항공 API 연동 (Amadeus / Skyscanner)
- [ ] 실제 호텔 API 연동 (Booking.com Affiliate / Expedia)
- [ ] 지원 여행지 확장 (`travel_agent._DEST_DATA`에 추가)
- [ ] Claude API 기반 일정 동적 생성 (`planner_agent`에 `anthropic` 클라이언트 추가)
- [ ] 일정 PDF 내보내기
- [ ] 다국어 지원 (현재 한국어 전용)
