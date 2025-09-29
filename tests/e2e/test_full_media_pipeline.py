# tests/e2e/test_full_media_pipeline.py
import pytest
import requests
import time
from uuid import uuid4

# The base URL for the API service as defined in docker-compose.test.yml
BASE_URL = "http://api:8000"

@pytest.fixture(scope="session")
def wait_for_api():
    """A fixture that waits for the API to be healthy before running tests."""
    start_time = time.time()
    while time.time() - start_time < 60: # 60-second timeout
        try:
            response = requests.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                print("API is healthy!")
                return
        except requests.ConnectionError:
            pass
        time.sleep(1)
    pytest.fail("API did not become healthy within 60 seconds.")

@pytest.fixture(scope="module")
def auth_token(wait_for_api):
    """Registers a new user and logs in to get an auth token for the tests."""
    email = f"testuser_{uuid4()}@example.com"
    password = "a_secure_password"

    requests.post(f"{BASE_URL}/auth/register", json={"email": email, "password": password})
    response = requests.post(f"{BASE_URL}/auth/token", json={"username": email, "password": password})
    response.raise_for_status()
    return response.json()["access_token"]

def test_full_audio_processing_pipeline(auth_token):
    """An end-to-end test for the full audio -> transcription -> summary pipeline."""
    # 1. Upload a small, valid WAV file (1 second of silence)
    wav_bytes = (
        b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00'
        b'\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
    )
    files = {"file": ("silence.wav", wav_bytes, "audio/wav")}
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    upload_response = requests.post(f"{BASE_URL}/media/", files=files, headers=headers)
    assert upload_response.status_code == 201, f"Upload failed: {upload_response.text}"
    media_id = upload_response.json()["id"]
    print(f"Uploaded media with ID: {media_id}")

    # 2. Poll for completion status
    start_time = time.time()
    media_status = ""
    while time.time() - start_time < 120: # 2-minute timeout
        status_response = requests.get(f"{BASE_URL}/media/{media_id}", headers=headers)
        if status_response.status_code == 200:
            media_status = status_response.json()["status"]
            print(f"Polling... status for media {media_id} is {media_status}")
            if media_status == "COMPLETED":
                break
            if media_status == "FAILED":
                pytest.fail(f"Media processing failed: {status_response.json().get('error_message')}")
        time.sleep(5)
    
    assert media_status == "COMPLETED", "Media processing did not complete within the timeout."

    # 3. Verify the final results
    print("Processing complete. Verifying final artifacts...")
    
    # Fetch transcription
    transcription_response = requests.get(f"{BASE_URL}/transcriptions/?media_id={media_id}", headers=headers)
    assert transcription_response.status_code == 200, f"Failed to fetch transcription: {transcription_response.text}"
    transcription_data = transcription_response.json()
    assert transcription_data["status"] == "COMPLETED"
    assert transcription_data["text"] is not None and len(transcription_data["text"]) > 0
    print(f"Transcription result: {transcription_data['text']}")

    # Fetch summary
    summary_response = requests.get(f"{BASE_URL}/summaries/?media_id={media_id}", headers=headers)
    assert summary_response.status_code == 200, f"Failed to fetch summary: {summary_response.text}"
    summary_data = summary_response.json()
    assert summary_data["status"] == "COMPLETED"
    assert summary_data["text"] is not None and len(summary_data["text"]) > 0
    print(f"Summary result: {summary_data['text']}")
