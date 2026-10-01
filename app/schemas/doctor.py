from datetime import time

from pydantic import Field, model_validator

from app.schemas.common import APIModel


class DoctorOut(APIModel):
    id: str
    name: str
    specialty: str
    license: str
    phone: str
    email: str
    clinic: str
    working_days: list[str]
    start_time: str
    end_time: str


class DoctorUpdate(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    specialty: str | None = Field(default=None, max_length=120)
    license: str | None = Field(default=None, max_length=80)
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=320)
    clinic: str | None = Field(default=None, max_length=240)
    working_days: list[str] | None = None
    start_time: time | None = None
    end_time: time | None = None

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        return self
