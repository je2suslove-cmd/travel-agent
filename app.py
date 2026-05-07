"""
Flask 웹 애플리케이션
실행: python3 app.py
"""
from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from urllib.parse import quote_plus

from flask import Flask, render_template, request
from flask_wtf.csrf import CSRFProtect

import flight_agent
import hotel_agent
import places_agent
import planner_agent
import weather_agent

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(32))
CSRFProtect(app)

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@app.template_filter('urlquote')
def urlquote_filter(s):
    return quote_plus(str(s))


@app.route("/")
def index():
    today = datetime.today().strftime("%Y-%m-%d")
    return render_template("index.html", today=today)


@app.route("/plan", methods=["POST"])
def plan():
    today = datetime.today().strftime("%Y-%m-%d")
    try:
        origin      = request.form.get("origin", "서울").strip() or "서울"
        destination = request.form.get("destination", "도쿄").strip() or "도쿄"
        start_date  = request.form.get("start_date", "")
        nights      = max(1, int(request.form.get("nights", 4)))
        passengers  = max(1, int(request.form.get("passengers", 2)))
        budget      = max(100_000, int(request.form.get("budget", 3_000_000)))
        style       = request.form.get("style", "휴양")

        if not start_date:
            start_date = today

        end_date = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=nights)).strftime("%Y-%m-%d")

        info = dict(
            origin=origin, destination=destination,
            start_date=start_date, end_date=end_date,
            nights=nights, passengers=passengers,
            budget=budget, style=style,
        )

        # 1. 항공편 에이전트
        flights = flight_agent.run(origin, destination, passengers)
        if not flights:
            return render_template("index.html", today=today,
                                   error=f"'{origin} → {destination}' 노선의 항공편을 찾을 수 없습니다.")
        selected_flight = flights[0]

        # 2. 호텔 에이전트
        remaining  = budget - selected_flight.price
        ppn_budget = max(int(remaining * 0.40 / nights), 50_000)
        hotels = hotel_agent.run(destination, nights, ppn_budget, style)
        selected_hotel = max(hotels, key=lambda h: (h.price_per_night <= ppn_budget, h.rating))
        costs = hotel_agent.calculate_costs(
            selected_flight.price, selected_hotel, nights, passengers, budget
        )

        # 3+4. 날씨·장소 에이전트 병렬 실행
        places_key = os.environ.get("GOOGLE_PLACES_KEY", "").strip()
        with ThreadPoolExecutor(max_workers=2) as pool:
            fut_weather = pool.submit(weather_agent.run, destination, start_date, nights)
            fut_places  = pool.submit(places_agent.run, destination, places_key)
            weather_days, clothing   = fut_weather.result()
            restaurants, attractions = fut_places.result()

        # 5. 일정 데이터 (웹 렌더링용)
        itinerary = planner_agent.get_data(
            info, selected_flight, selected_hotel, costs,
            weather_days=weather_days,
            restaurants=restaurants,
            attractions=attractions,
        )

        return render_template(
            "result.html",
            info=info,
            flights=flights,
            selected_flight=selected_flight,
            hotels=hotels,
            selected_hotel=selected_hotel,
            costs=costs,
            weather_days=weather_days,
            clothing=clothing,
            restaurants=restaurants,
            attractions=attractions,
            itinerary=itinerary,
            ppn_budget=ppn_budget,
            has_places=bool(places_key),
        )

    except ValueError as exc:
        logger.error("입력값 오류: %s", exc, exc_info=True)
        return render_template("index.html", today=today,
                               error="입력값이 올바르지 않습니다. 숫자 항목을 확인해주세요.")
    except Exception as exc:
        logger.error("일정 생성 실패: %s", exc, exc_info=True)
        return render_template("index.html", today=today,
                               error="일정 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug, port=5000)
