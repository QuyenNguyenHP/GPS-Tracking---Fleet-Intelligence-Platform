from datetime import timedelta
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.db import utcnow


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Location(Contract):
    fix_valid: bool
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    speed_kmh: float | None = Field(default=None, ge=0, le=400)
    heading_deg: float | None = Field(default=None, ge=0, lt=360)
    satellites: int | None = Field(default=None, ge=0, le=100)
    hdop: float | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def valid_coordinates(self):
        if self.fix_valid and (self.latitude is None or self.longitude is None):
            raise ValueError("Valid fixes require latitude and longitude")
        if not self.fix_valid and (self.latitude is not None or self.longitude is not None):
            raise ValueError("No-fix heartbeats must omit coordinates")
        return self


class Status(Contract):
    network_type: Literal["wifi", "lte", "simulator"] = "wifi"
    battery_percent: float | None = Field(default=None, ge=0, le=100)
    external_power: bool = True
    firmware_version: str = Field(default="unknown", max_length=64)


class Telemetry(Contract):
    schema_version: Literal[1]
    device_id: str = Field(min_length=1, max_length=64)
    sequence_number: int = Field(ge=0, le=9223372036854775807, strict=True)
    recorded_at: AwareDatetime
    location: Location
    status: Status = Field(default_factory=Status)

    @model_validator(mode="after")
    def plausible_time(self):
        if self.recorded_at > utcnow() + timedelta(minutes=5):
            raise ValueError("recorded_at is more than five minutes in the future")
        if self.recorded_at.year < 2020:
            raise ValueError("recorded_at must be in 2020 or later")
        return self


class Batch(Contract):
    samples: list[Telemetry] = Field(min_length=1, max_length=200)
