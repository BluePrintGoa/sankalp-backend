import asyncio
from datetime import date, time

from sqlalchemy import select

from app.database import SessionLocal, init_db
from app.models import Appointment, Doctor, Patient, User
from app.utils.security import hash_password

SEED_DATE = date(2026, 10, 1)

PATIENTS = [
    {
        "id": "PT-2048", "name": "Amelia Hart", "date_of_birth": date(1989, 4, 16),
        "sex": "Female", "blood_group": "A+", "height_cm": 168, "weight_kg": 63.4,
        "phone": "+1 (415) 555-0148", "email": "amelia.hart@example.com",
        "conditions": ["Mild asthma", "Seasonal allergic rhinitis"], "allergies": ["Penicillin", "Tree nuts"],
        "medications": ["Albuterol inhaler · 90 mcg as needed", "Cetirizine · 10 mg daily"], "last_visit": date(2026, 9, 18),
    },
    {
        "id": "PT-1932", "name": "Noah Williams", "date_of_birth": date(1976, 11, 2),
        "sex": "Male", "blood_group": "O−", "height_cm": 181, "weight_kg": 82.1,
        "phone": "+1 (415) 555-0193", "email": "noah.williams@example.com",
        "conditions": ["Hypertension"], "allergies": ["Sulfa drugs"],
        "medications": ["Lisinopril · 10 mg daily"], "last_visit": date(2026, 9, 22),
    },
    {
        "id": "PT-1756", "name": "Sofia Chen", "date_of_birth": date(1995, 7, 27),
        "sex": "Female", "blood_group": "B+", "height_cm": 163, "weight_kg": 57.8,
        "phone": "+1 (415) 555-0175", "email": "sofia.chen@example.com",
        "conditions": ["Migraine"], "allergies": [],
        "medications": ["Sumatriptan · 50 mg as needed"], "last_visit": date(2026, 9, 24),
    },
    {
        "id": "PT-1684", "name": "Ethan Brooks", "date_of_birth": date(1964, 2, 10),
        "sex": "Male", "blood_group": "AB+", "height_cm": 175, "weight_kg": 76.2,
        "phone": "+1 (415) 555-0168", "email": "ethan.brooks@example.com",
        "conditions": ["Type 2 diabetes"], "allergies": ["Latex"],
        "medications": ["Metformin · 500 mg twice daily"], "last_visit": date(2026, 9, 26),
    },
]

APPOINTMENTS = [
    ("AP-4101", "PT-2048", time(9, 0), 30, "Follow-up", "checked_in"),
    ("AP-4102", "PT-1932", time(9, 45), 30, "Blood pressure review", "scheduled"),
    ("AP-4103", "PT-1756", time(10, 30), 45, "New patient", "scheduled"),
    ("AP-4104", "PT-1684", time(11, 30), 30, "Diabetes check-in", "scheduled"),
    ("AP-4105", "PT-1932", time(13, 30), 30, "Lab results", "scheduled"),
]


async def seed() -> None:
    await init_db()
    async with SessionLocal() as db:
        doctor_user = await db.scalar(select(User).where(User.email == "maya.patel@northstar.health"))
        if doctor_user is None:
            doctor_user = User(
                email="maya.patel@northstar.health",
                hashed_password=hash_password("doctor123"),
                role="doctor",
            )
            db.add(doctor_user)
            await db.flush()
            doctor = Doctor(
                public_id="DR-0081", user_id=doctor_user.id, name="Dr. Maya Patel",
                specialty="Internal medicine", license_number="CA · A129844",
                phone="+1 (415) 555-0081", email=doctor_user.email,
                clinic="Northstar Medical · Suite 240",
                working_days=["Mon", "Tue", "Wed", "Thu", "Fri"],
                start_time=time(8, 30), end_time=time(17, 0),
            )
            db.add(doctor)
            await db.flush()
        else:
            doctor = await db.scalar(select(Doctor).where(Doctor.user_id == doctor_user.id))

        patient_by_public_id = {}
        for data in PATIENTS:
            patient = await db.scalar(select(Patient).where(Patient.public_id == data["id"]))
            if patient is None:
                user = await db.scalar(select(User).where(User.email == data["email"]))
                if user is None:
                    user = User(email=data["email"], hashed_password=hash_password("patient123"), role="patient")
                    db.add(user)
                    await db.flush()
                values = {key: value for key, value in data.items() if key != "id"}
                patient = Patient(public_id=data["id"], user_id=user.id, **values)
                db.add(patient)
                await db.flush()
            patient_by_public_id[patient.public_id] = patient

        for public_id, patient_id, appointment_time, duration, appointment_type, status in APPOINTMENTS:
            found = await db.scalar(select(Appointment).where(Appointment.public_id == public_id))
            if found is None:
                db.add(Appointment(
                    public_id=public_id,
                    patient_id=patient_by_public_id[patient_id].id,
                    doctor_id=doctor.id,
                    appointment_date=SEED_DATE,
                    time=appointment_time,
                    duration_minutes=duration,
                    type=appointment_type,
                    status=status,
                ))
        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed())
