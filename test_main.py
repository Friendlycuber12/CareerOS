from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_index():
    response = client.get("/")
    assert response.status_code == 200
    assert "CareerOS" in response.text

def test_read_login():
    response = client.get("/login")
    assert response.status_code == 200
    assert "Login" in response.text

def test_read_signup():
    response = client.get("/signup")
    assert response.status_code == 200
    assert "Sign Up" in response.text

def test_read_dashboard():
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "Dashboard" in response.text

def test_read_roadmap():
    response = client.get("/roadmap")
    assert response.status_code == 200
    assert "Roadmap" in response.text

def test_read_applications():
    response = client.get("/applications")
    assert response.status_code == 200
    assert "Application Tracker" in response.text

def test_read_coding():
    response = client.get("/coding")
    assert response.status_code == 200
    assert "Coding Analytics" in response.text

def test_read_resume():
    response = client.get("/resume")
    assert response.status_code == 200
    assert "Resume Analyzer" in response.text

def test_read_interviews():
    response = client.get("/interviews")
    assert response.status_code == 200
    assert "Mock Interviews" in response.text

def test_read_assistant():
    response = client.get("/assistant")
    assert response.status_code == 200
    assert "AI Assistant" in response.text

def test_read_settings():
    response = client.get("/settings")
    assert response.status_code == 200
    assert "Settings" in response.text
