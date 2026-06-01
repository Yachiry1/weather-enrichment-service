import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from kombu.exceptions import OperationalError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db, init_db
from app.models import City, WeatherStatus
from app.schemas import CityCreate, CityRead, HealthRead
from app.tasks import refresh_weather


settings = get_settings()
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def normalize_city_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


@app.on_event("startup")
def startup() -> None:
    init_db()

def get_city_location(city_name: str, client: httpx.Client) -> dict:
    response = client.get(
        settings.weather_geocoding_url,
        params={
            "name": city_name,
            "count": 1,
            "language": "en",
            "format": "json",
        },
    )

    response.raise_for_status()

    locations = response.json().get("results", [])
    if not locations:
        raise ValueError(f"City not found: {city_name}")

    return locations[0]


def resolve_city_location(city_name: str) -> dict:
    try:
        with httpx.Client(timeout=15.0) as client:
            location = get_city_location(city_name, client)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not validate city with weather provider",
        ) from exc

    return location


def queue_weather_refresh(city: City, db: Session) -> None:
    city.status = WeatherStatus.pending
    city.error = None
    db.commit()
    db.refresh(city)

    try:
        task = refresh_weather.delay(city.id)
    except OperationalError as exc:
        city.status = WeatherStatus.failed
        city.error = "Could not connect to Redis broker"
        db.commit()
        db.refresh(city)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not queue weather refresh task",
        ) from exc

    city.task_id = task.id
    db.commit()
    db.refresh(city)


@app.get("/health", response_model=HealthRead)
def get_health() -> HealthRead:
    return HealthRead(status="ok")


@app.post("/cities", response_model=CityRead, status_code=status.HTTP_202_ACCEPTED)
def post_cities(payload: CityCreate, db: Session = Depends(get_db)) -> City:
    location = resolve_city_location(payload.name)
    city_name = location["name"]

    city = City(
        name=city_name,
        normalized_name=normalize_city_name(city_name),
        latitude=location.get("latitude"),
        longitude=location.get("longitude"),
    )
    db.add(city)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()

        existing_city = db.scalars(
            select(City).where(City.normalized_name == city.normalized_name)
        ).first()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "City already exists",
                "city_id": existing_city.id if existing_city else None,
            },
        ) from exc

    db.refresh(city)
    queue_weather_refresh(city, db)
    return city


@app.get("/cities", response_model=list[CityRead])
def get_cities(db: Session = Depends(get_db)) -> list[City]:
    return list(db.scalars(select(City).order_by(City.created_at.desc())).all())


@app.get("/cities/{city_id}", response_model=CityRead)
def get_city(city_id: int, db: Session = Depends(get_db)) -> City:
    city = db.get(City, city_id)
    if city is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="City not found",
        )
    return city


@app.delete("/cities/{city_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_city(city_id: int, db: Session = Depends(get_db)) -> None:
    city = db.get(City, city_id)
    if city is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="City not found",
        )

    db.delete(city)
    db.commit()


@app.post("/cities/{city_id}/refresh", response_model=CityRead, status_code=status.HTTP_202_ACCEPTED)
def refresh_city(city_id: int, db: Session = Depends(get_db)) -> City:
    city = db.get(City, city_id)
    if city is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="City not found",
        )

    queue_weather_refresh(city, db)
    return city

