from datetime import date, datetime

from pydantic import Field

from app.schemas.common import APIModel


class PatientOut(APIModel):
    id: str
    name: str
    date_of_birth: date
    sex: str
    blood_group: str
    height_cm: int
    weight_kg: float
    phone: str
    email: str
    conditions: list[str]
    allergies: list[str]
    medications: list[str]
    last_visit: date | None
    storage_used_bytes: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PatientUpdate(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    date_of_birth: date | None = None
    sex: str | None = Field(default=None, max_length=40)
    blood_group: str | None = Field(default=None, max_length=8)
    height_cm: int | None = Field(default=None, ge=0, le=300)
    weight_kg: float | None = Field(default=None, ge=0, le=1000)
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=320)
    conditions: list[str] | None = None
    allergies: list[str] | None = None
    medications: list[str] | None = None
    last_visit: date | None = None
