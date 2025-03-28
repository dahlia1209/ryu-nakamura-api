from fastapi import FastAPI
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

def test_connection():
    response = client.get("/health")
    assert response.status_code == 200