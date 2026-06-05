from datetime import UTC, datetime

import httpx
from celery import Celery
from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models import City, WeatherStatus


settings = get_settings()

celery_app = Celery(
    "weather_enrichment",
    broker=settings.redis_url,
    backend=settings.redis_url,
    broker_connection_retry_on_startup=True,
)

celery_app.conf.beat_schedule = {
    "refresh_all_weather_every_minute": {
        "task": "app.tasks.refresh_all_weather",
        "schedule": 60,
    }
}

WEATHER_CODE_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
}


@celery_app.task(name="app.tasks.refresh_all_weather")
def refresh_all_weather() -> int:
    db = SessionLocal()
    try:
        city_ids = list(db.scalars(select(City.id)).all())
    finally:
        db.close()

    for city_id in city_ids:
        refresh_weather.delay(city_id)

    return len(city_ids)


@celery_app.task(name="app.tasks.refresh_weather")
def refresh_weather(city_id: int) -> None:
    db = SessionLocal()
    try:
        city = db.get(City, city_id)
        if city is None:
            return

        city.status = WeatherStatus.processing
        city.error = None
        db.commit()

        with httpx.Client(timeout=15.0) as client:
            latitude = city.latitude
            longitude = city.longitude

            if latitude is None or longitude is None:
                geocoding_response = client.get(
                    settings.weather_geocoding_url,
                    params={"name": city.name, "count": 1, "language": "en", "format": "json"},
                )
                geocoding_response.raise_for_status()
                locations = geocoding_response.json().get("results", [])
                if not locations:
                    raise ValueError(f"City not found: {city.name}")

                location = locations[0]
                latitude = location["latitude"]
                longitude = location["longitude"]
                city.latitude = latitude
                city.longitude = longitude

            forecast_response = client.get(
                settings.weather_forecast_url,
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "current": "temperature_2m,relative_humidity_2m,weather_code",
                    "timezone": "auto",
                },
            )
            forecast_response.raise_for_status()
            current = forecast_response.json().get("current", {})

        weather_code = current.get("weather_code")
        city.temperature = current.get("temperature_2m")
        city.humidity = current.get("relative_humidity_2m")
        city.description = WEATHER_CODE_DESCRIPTIONS.get(weather_code, "Unknown")
        city.status = WeatherStatus.completed
        city.last_refreshed_at = datetime.now(UTC)
        db.commit()
    except Exception as exc:
        city = db.get(City, city_id)
        if city is not None:
            city.status = WeatherStatus.failed
            city.error = str(exc)
            db.commit()
        raise
    finally:
        db.close()
