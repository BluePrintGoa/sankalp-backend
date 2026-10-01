import uuid
from datetime import time

from sqlalchemy import ForeignKey, JSON, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.database import Base


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    specialty: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    license_number: Mapped[str] = mapped_column("license", String(80), default="", nullable=False)
    phone: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    clinic: Mapped[str] = mapped_column(String(240), default="", nullable=False)
    working_days: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, default=time(8, 30), nullable=False)
    end_time: Mapped[time] = mapped_column(Time, default=time(17, 0), nullable=False)

    user: Mapped["User"] = relationship(back_populates="doctor")
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="doctor")
