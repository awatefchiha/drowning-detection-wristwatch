import os
import hmac
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="AquaGuard API")

# Device key comes from an environment variable, never from the code
DEVICE_API_KEY = os.environ.get("DEVICE_API_KEY", "")


class Reading(BaseModel):
    # Pydantic rejects anything outside these ranges (input validation)
    device_id: str = Field(pattern=r"^watch-\d{3}$")
    uptime_s: int = Field(ge=0)
    accel_x: float = Field(ge=-16, le=16)
    accel_y: float = Field(ge=-16, le=16)
    accel_z: float = Field(ge=-16, le=16)
    movement_variance: float = Field(ge=0, le=100)
    heart_rate: int = Field(ge=20, le=250)
    time_underwater: int = Field(ge=0, le=3600)


LATEST: list[dict] = []   # temporary in-memory store, replaced by a database later


def check_key(key: str | None) -> None:
    # constant-time comparison avoids leaking the key through timing
    if not DEVICE_API_KEY or not key or not hmac.compare_digest(
        key.encode(), DEVICE_API_KEY.encode()
    ):
        raise HTTPException(status_code=401, detail="invalid api key")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest", status_code=201)
def ingest(reading: Reading, x_api_key: str | None = Header(default=None)):
    check_key(x_api_key)
    # server stamps the time; the device clock isn't trusted
    row = reading.model_dump() | {"received_at": datetime.now(timezone.utc).isoformat()}
    LATEST.append(row)
    del LATEST[:-100]     # keep only the last 100 readings
    return {"ok": True}


@app.get("/debug/latest")   # temporary: remove once the database exists
def debug_latest(x_api_key: str | None = Header(default=None)):
    check_key(x_api_key)
    return LATEST
