# ✈️ AI 여행 플래너

출발지·여행지·날짜·인원·예산·스타일을 입력하면  
**항공편 · 호텔 · 날씨 · 관광지 · 상세 일정**을 한 번에 생성해주는 여행 계획 웹 앱입니다.

---

## 화면 미리보기

| 입력 폼 | 결과 페이지 |
|--------|------------|
| 출발지·여행지·날짜·인원·예산·스타일 선택 | 항공편·호텔·날씨·일정·관광지 통합 결과 |

---

## 주요 기능

- **실시간 항공편** — Travelpayouts Aviasales API, 날짜별 최저가 조회 (키 없으면 Mock 자동 전환)
- **실제 호텔 목록** — Google Places API, 평점·위치 기반 추천 + 목적지별 요금 추정
- **날씨 예보** — Open-Meteo 무료 API, 16일 이내 예보 / 초과 시 전년 동기 기후 참고값
- **음식점·관광지** — Google Places Text Search, 좌표 바이어스 현지 결과
- **맞춤 일정** — 10개 여행지 × 3개 스타일(휴양·액티비티·맛집) × 최대 4일 상세 일정
- **옷차림 추천** — 기온·강수량 기반 자동 추천
- **예산 관리** — 항공+숙박+식비 자동 계산, 초과 여부 표시

---

## 지원 여행지

도쿄 · 오사카 · 방콕 · 파리 · 제주 · 싱가포르 · 발리 · 홍콩 · 뉴욕 · 다낭  
*(그 외 도시 입력 시 기본 일정으로 대체)*

---

## 시작하기

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정

| 변수 | 필수 | 설명 |
|------|------|------|
| `TRAVELPAYOUTS_TOKEN` | 선택 | 실시간 항공편 요금 ([발급](https://www.travelpayouts.com/)) |
| `GOOGLE_PLACES_KEY` | 선택 | 실제 호텔·음식점·관광지 데이터 ([발급](https://console.cloud.google.com/)) |
| `SECRET_KEY` | 선택 | Flask 세션 시크릿 키 (미설정 시 매 실행마다 랜덤 생성) |
| `FLASK_DEBUG` | 선택 | `1` 설정 시 디버그 모드 활성화 |

```bash
export TRAVELPAYOUTS_TOKEN="your_token"
export GOOGLE_PLACES_KEY="your_key"
```

> API 키 없이도 Mock 데이터로 전체 기능 동작합니다.

### 3. 실행

**웹 UI (Flask)**
```bash
python app.py
# → http://localhost:5000
```

**CLI (터미널 대화형)**
```bash
python travel_agent.py
```

---

## 아키텍처

```
웹(app.py) ──┐
             ├──▶ flight_agent ──▶ hotel_agent ──▶ weather_agent ──▶ places_agent ──▶ planner_agent
CLI(travel_agent.py) ──┘
```

### 에이전트별 역할

| 파일 | 역할 | 데이터 소스 |
|------|------|------------|
| `flight_agent.py` | 항공편 검색, 최저가 정렬 | Travelpayouts API → Mock 폴백 |
| `hotel_agent.py` | 호텔 검색, 비용 계산 | Google Places API → Mock 폴백 |
| `weather_agent.py` | 날씨 예보 + 옷차림 추천 | Open-Meteo (무료, 키 불필요) |
| `places_agent.py` | 음식점·관광지 검색 | Google Places API |
| `planner_agent.py` | 일정 조합 (웹/CLI 듀얼 출력) | `destinations.py` |
| `destinations.py` | 여행지 콘텐츠 데이터 | 내장 데이터 |

### 핵심 데이터 흐름

```
① 항공편 조회 (Travelpayouts calendar API)
② 호텔 예산 계산 = (총예산 - 항공료) × 40% ÷ 숙박일수
③ 호텔 조회 (Google Places Nearby Search)
④ 날씨 + 장소 병렬 조회 (ThreadPoolExecutor)
⑤ 일정 생성 (destinations.py 콘텐츠 + 날씨 데이터 통합)
```

---

## API 연동 상세

### 항공편 — Travelpayouts Aviasales

- 엔드포인트: `GET /v1/prices/calendar`
- 요청 날짜가 포함된 월 전체 캘린더 조회 → 해당 날짜 우선, 최저가 3개 선택
- `duration_to` 필드 없을 시 노선별 기준 소요 시간으로 보완
- 지원 노선 10개 (서울 기준), 미지원 노선은 Mock 데이터

### 호텔 — Google Places

- 엔드포인트: `GET /nearbysearch` (type=lodging, 반경 12km)
- 평점 3.8+ 필터 → 평점·리뷰수 가중 정렬
- 별점 추정: ≥4.5 → 5성 / ≥4.1 → 4성 / ≥3.7 → 3성
- 가격 추정: 목적지 × 별점 기준가 + 인기도 보정 (±20%)

### 날씨 — Open-Meteo

- 16일 이내: 실시간 예보 API
- 16일 초과: 전년 동기 아카이브 API (기후 경향 참고)
- 결과 1시간 인메모리 캐시 (thread-safe)

### 음식점·관광지 — Google Places

- `textsearch` + 좌표 바이어스 (반경 15km)로 현지 결과만 필터링

---

## 프로젝트 구조

```
travel-agent/
├── app.py               # Flask 웹 서버
├── travel_agent.py      # CLI 인터랙티브 스크립트
├── orchestrator.py      # CLI 멀티에이전트 오케스트레이터
├── flight_agent.py      # 항공편 에이전트
├── hotel_agent.py       # 호텔 에이전트
├── weather_agent.py     # 날씨 에이전트
├── places_agent.py      # 음식점·관광지 에이전트
├── planner_agent.py     # 일정 생성 에이전트
├── destinations.py      # 여행지 콘텐츠 데이터
├── templates/
│   ├── index.html       # 입력 폼
│   └── result.html      # 결과 페이지
└── requirements.txt
```

---

## 향후 계획

- [ ] Hotellook API 연동으로 실제 호텔 요금 조회
- [ ] Amadeus / Skyscanner API 교체
- [ ] 지원 여행지 확장 (`destinations.py`에 추가)
- [ ] Claude API 기반 일정 동적 생성
- [ ] 일정 PDF 내보내기
- [ ] 다국어 지원

---

## 라이선스

MIT
