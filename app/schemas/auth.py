from datetime import date, datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import APIModel
from app.schemas.doctor import DoctorOut
from app.schemas.patient import PatientOut


class RegisterRequest(APIModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    role: Literal["patient", "doctor"]
    name: str = Field(min_length=1, max_length=160)
    date_of_birth: date | None = None
    sex: str = "Unspecified"
    blood_group: str = "Unknown"
    height_cm: int = Field(default=0, ge=0, le=300)
    weight_kg: float = Field(default=0, ge=0, le=1000)
    phone: str = ""
    specialty: str = ""
    license: str = ""
    clinic: str = ""
    working_days: list[str] = Field(default_factory=list)


class LoginRequest(APIModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class UserOut(APIModel):
    id: str
    email: str
    role: Literal["patient", "doctor"]
    is_active: bool
    created_at: datetime
    patient: PatientOut | None = None
    doctor: DoctorOut | None = None


class AuthResponse(APIModel):
    user: UserOut
    message: str = "Authenticated"
