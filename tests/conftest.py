import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-characters")
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault("ALLOW_DOCTOR_REGISTRATION", "true")
os.environ.setdefault("UPLOAD_DIR", "./test-uploads")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
