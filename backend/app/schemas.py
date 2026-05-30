from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import WeatherStatus


class CityCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120, examples=["Kyiv"])

    @field_validator("name")
    @classmethod
    def normalize_input(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("City name cannot be empty")
        return value


class CityRead(BaseModel):
    id: int
    name: str
    latitude: float | None = None
    longitude: float | None = None
    temperature: float | None = None
    humidity: int | None = None
    description: str | None = None
    status: WeatherStatus
    error: str | None = None
    task_id: str | None = None
    last_refreshed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HealthRead(BaseModel):
    status: str
