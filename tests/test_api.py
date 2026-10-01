from io import BytesIO


def register(client, email, role, name):
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "StrongPass123", "role": role, "name": name},
    )
    assert response.status_code == 201, response.text
    return response.json()


def login(client, email):
    response = client.post("/auth/login", json={"email": email, "password": "StrongPass123"})
    assert response.status_code == 200, response.text
    assert client.cookies.get("access_token")
    assert client.cookies.get("refresh_token")
    return response.json()


def csrf_headers(client):
    return {"X-CSRF-Token": client.cookies.get("csrf_token")}


def test_registration_login_refresh_and_me(client):
    register(client, "patient1@example.test", "patient", "Test Patient")
    login(client, "patient1@example.test")

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "patient"
    assert me.json()["patient"]["name"] == "Test Patient"

    refresh = client.post("/auth/refresh", headers=csrf_headers(client))
    assert refresh.status_code == 200
    assert refresh.json()["message"] == "Tokens refreshed"

    rejected = client.post("/auth/logout")
    assert rejected.status_code == 403


def test_doctor_self_registration_can_be_disabled(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "allow_doctor_registration", False)
    response = client.post(
        "/auth/register",
        json={"email": "closed-doctor@example.test", "password": "StrongPass123", "role": "doctor", "name": "Unverified"},
    )
    assert response.status_code == 403


def test_patient_schedule_is_authenticated(client):
    register(client, "schedule-patient@example.test", "patient", "Schedule Patient")
    login(client, "schedule-patient@example.test")
    response = client.get("/appointments/mine")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_patient_access_is_scoped_and_doctor_can_update(client):
    patient = register(client, "patient2@example.test", "patient", "Patient Two")
    own_patient_id = patient["patient"]["id"]
    other = register(client, "patient3@example.test", "patient", "Patient Three")

    login(client, "patient2@example.test")
    assert client.get(f"/patients/{own_patient_id}").status_code == 200
    assert client.get(f"/patients/{other['patient']['id']}").status_code == 403
    assert client.get("/patients").status_code == 403

    client.post("/auth/logout", headers=csrf_headers(client))
    register(client, "doctor@example.test", "doctor", "Test Doctor")
    login(client, "doctor@example.test")
    assert client.get("/patients").status_code == 200
    updated = client.patch(
        f"/patients/{own_patient_id}",
        json={"conditions": ["Updated condition"]},
        headers=csrf_headers(client),
    )
    assert updated.status_code == 200
    assert updated.json()["conditions"] == ["Updated condition"]


def test_file_upload_download_delete_and_quota_accounting(client):
    patient = register(client, "patient4@example.test", "patient", "File Patient")
    patient_id = patient["patient"]["id"]
    register(client, "doctor2@example.test", "doctor", "File Doctor")
    login(client, "doctor2@example.test")

    upload = client.post(
        f"/patients/{patient_id}/files",
        files={"file": ("report.txt", BytesIO(b"medical report"), "text/plain")},
        headers=csrf_headers(client),
    )
    assert upload.status_code == 201, upload.text
    metadata = upload.json()
    assert metadata["name"] == "report.txt"
    assert metadata["size"] == len(b"medical report")

    downloaded = client.get(metadata["url"])
    assert downloaded.status_code == 200
    assert downloaded.content == b"medical report"
    assert client.get(f"/patients/{patient_id}").json()["storageUsedBytes"] == len(b"medical report")

    removed = client.delete(
        f"/patients/{patient_id}/files/{metadata['id']}", headers=csrf_headers(client)
    )
    assert removed.status_code == 204
    assert client.get(f"/patients/{patient_id}/files").json() == []
    assert client.get(f"/patients/{patient_id}").json()["storageUsedBytes"] == 0


def test_doctor_profile_schedule_and_patient_qr(client):
    patient = register(client, "patient5@example.test", "patient", "QR Patient")
    patient_id = patient["patient"]["id"]
    register(client, "doctor3@example.test", "doctor", "Schedule Doctor")
    login(client, "doctor3@example.test")

    profile = client.get("/doctors/me")
    assert profile.status_code == 200
    updated = client.patch(
        "/doctors/me",
        json={"workingDays": ["Mon", "Wed"], "startTime": "09:00"},
        headers=csrf_headers(client),
    )
    assert updated.status_code == 200
    assert updated.json()["startTime"] == "09:00"
    assert updated.json()["workingDays"] == ["Mon", "Wed"]

    invalid_schedule = client.patch(
        "/doctors/me", json={"startTime": "18:00"}, headers=csrf_headers(client)
    )
    assert invalid_schedule.status_code == 422
    qr = client.get(f"/patients/{patient_id}/qr")
    assert qr.status_code == 200
    assert qr.headers["content-type"].startswith("image/svg+xml")


def test_upload_rejects_patient_over_quota(client, monkeypatch):
    from app.config import settings

    patient = register(client, "patient6@example.test", "patient", "Quota Patient")
    register(client, "doctor4@example.test", "doctor", "Quota Doctor")
    login(client, "doctor4@example.test")
    monkeypatch.setattr(settings, "max_file_storage_mb", 0)

    rejected = client.post(
        f"/patients/{patient['patient']['id']}/files",
        files={"file": ("large.txt", BytesIO(b"over quota"), "text/plain")},
        headers=csrf_headers(client),
    )
    assert rejected.status_code == 413
    assert client.get(f"/patients/{patient['patient']['id']}/files").json() == []
