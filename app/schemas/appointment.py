from __future__ import annotations

from datetime import date as date_type, time as time_type
from typing import Literal

from pydantic import Field

from app.schemas.common import APIModel

AppointmentStatus = Literal["Scheduled", "Checked in", "Completed", "scheduled", "checked_in", "completed"]


class AppointmentOut(APIModel):
    id: str
    patient_id: str
    patient_name: str
    doctor_id: str
    date: date_type
    time: str
    duration_minutes: int
    type: str
    status: str


class AppointmentUpdate(APIModel):
    date: date_type | None = None
    time: time_type | None = None
    duration_minutes: int | None = Field(default=None, ge=5, le=480)
    type: str | None = Field(default=None, min_length=1, max_length=120)
    status: AppointmentStatus | None = None
