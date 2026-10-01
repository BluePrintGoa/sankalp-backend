from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_csrf, require_roles
from app.database import get_db
from app.models import User
from app.schemas.doctor import DoctorOut, DoctorUpdate
from app.services.serializers import doctor_data

router = APIRouter(prefix="/doctors", tags=["doctors"])


@router.get("/me", response_model=DoctorOut)
async def own_profile(user: User = Depends(require_roles("doctor"))):
    if user.doctor is None:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    return doctor_data(user.doctor)


@router.patch("/me", response_model=DoctorOut, dependencies=[Depends(require_csrf)])
async def update_profile(
    changes: DoctorUpdate,
    user: User = Depends(require_roles("doctor")),
    db: AsyncSession = Depends(get_db),
):
    if user.doctor is None:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    fields = changes.model_dump(exclude_unset=True)
    start_time = fields.get("start_time", user.doctor.start_time)
    end_time = fields.get("end_time", user.doctor.end_time)
    if start_time >= end_time:
        raise HTTPException(status_code=422, detail="start_time must be before end_time")
    if "license" in fields:
        fields["license_number"] = fields.pop("license")
    for field, value in fields.items():
        setattr(user.doctor, field, value)
    await db.commit()
    await db.refresh(user.doctor)
    return doctor_data(user.doctor)
