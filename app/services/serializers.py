from app.models import Appointment, Doctor, Patient, User


def patient_data(patient: Patient) -> dict:
    return {
        "id": patient.public_id,
        "name": patient.name,
        "date_of_birth": patient.date_of_birth,
        "sex": patient.sex,
        "blood_group": patient.blood_group,
        "height_cm": patient.height_cm,
        "weight_kg": patient.weight_kg,
        "phone": patient.phone,
        "email": patient.email,
        "conditions": patient.conditions,
        "allergies": patient.allergies,
        "medications": patient.medications,
        "last_visit": patient.last_visit,
        "storage_used_bytes": patient.storage_used_bytes,
        "created_at": patient.created_at,
        "updated_at": patient.updated_at,
    }


def doctor_data(doctor: Doctor) -> dict:
    return {
        "id": doctor.public_id,
        "name": doctor.name,
        "specialty": doctor.specialty,
        "license": doctor.license_number,
        "phone": doctor.phone,
        "email": doctor.email,
        "clinic": doctor.clinic,
        "working_days": doctor.working_days,
        "start_time": doctor.start_time.strftime("%H:%M"),
        "end_time": doctor.end_time.strftime("%H:%M"),
    }


def appointment_data(appointment: Appointment) -> dict:
    labels = {"scheduled": "Scheduled", "checked_in": "Checked in", "completed": "Completed"}
    return {
        "id": appointment.public_id,
        "patient_id": appointment.patient.public_id,
        "patient_name": appointment.patient.name,
        "doctor_id": appointment.doctor.public_id,
        "date": appointment.appointment_date,
        "time": appointment.time.strftime("%H:%M"),
        "duration_minutes": appointment.duration_minutes,
        "type": appointment.type,
        "status": labels.get(appointment.status, appointment.status),
    }


def user_data(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "patient": patient_data(user.patient) if user.patient else None,
        "doctor": doctor_data(user.doctor) if user.doctor else None,
    }
