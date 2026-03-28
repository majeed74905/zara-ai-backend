from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome to Zara AI" in response.json().get("message", "")

def test_docs_health():
    response = client.get("/docs")
    assert response.status_code == 200
