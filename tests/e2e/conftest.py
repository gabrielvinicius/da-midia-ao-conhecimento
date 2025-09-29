# tests/e2e/conftest.py
import pytest
import requests
import time
from uuid import uuid4

# The base URL for the API service as defined in docker-compose.test.yml
BASE_URL = "http://api:8000"

@pytest.fixture(scope="session")
def wait_for_api():
    """Waits for the API to be healthy before running any tests."""
    start_time = time.time()
    while time.time() - start_time < 60:  # 60-second timeout
        try:
            response = requests.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                print("API is healthy!")
                return
        except requests.ConnectionError:
            print("API not ready, waiting...")
        time.sleep(2)
    pytest.fail("API did not become healthy within 60 seconds.")

@pytest.fixture(scope="module")
def auth_token(wait_for_api):
    """Registers a new user and logs in to get an auth token for the test module."""
    email = f"testuser_{uuid4()}@example.com"
    password = "a_secure_password_for_e2e"

    # Register
    reg_response = requests.post(f"{BASE_URL}/auth/register", json={"email": email, "password": password})
    assert reg_response.status_code == 201, f"Failed to register user: {reg_response.text}"

    # Login
    login_response = requests.post(f"{BASE_URL}/auth/token", json={"username": email, "password": password})
    login_response.raise_for_status()
    token = login_response.json()["access_token"]
    print(f"Obtained auth token for user {email}")
    return token
