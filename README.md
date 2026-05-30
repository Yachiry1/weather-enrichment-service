## Weather Enrichment Service

Service for saving cities and asynchronously enriching them with current weather data.

### Stack

- Backend: FastAPI, SQLAlchemy, PostgreSQL
- Background jobs: Celery + Redis
- Weather API: Open-Meteo
- Frontend: Angular
- Infrastructure: Docker Compose

### Run

Create `.env` from `.env.example` if needed, then start the full stack:

```bash
docker compose up --build
```

Services:

- Frontend: http://localhost:4200
- Backend API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs

### Environment

Main variables:

```env
APP_NAME=Weather Enrichment Service
DATABASE_URL=postgresql://weather:weather@postgres:5432/weather
REDIS_URL=redis://redis:6379/0
WEATHER_GEOCODING_URL=https://geocoding-api.open-meteo.com/v1/search
WEATHER_FORECAST_URL=https://api.open-meteo.com/v1/forecast
```

### API

- `GET /health` - health check
- `POST /cities` - add city and queue weather refresh
- `GET /cities` - list cities with saved weather data
- `GET /cities/{city_id}` - get one city
- `POST /cities/{city_id}/refresh` - manually refresh weather

### Stop

```bash
docker compose down
```

Stop and remove PostgreSQL data:

```bash
docker compose down -v
```
