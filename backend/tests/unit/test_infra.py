"""Unit Tests for Core Infrastructure Components (Settings, FastAPI, Health)."""

import unittest
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.config import settings

client = TestClient(app)


class TestInfrastructureScaffold(unittest.TestCase):
    
    def test_settings_load(self):
        self.assertEqual(settings.PROJECT_NAME, "Enterprise AI Digital Assistant")
        self.assertEqual(settings.API_V1_STR, "/api/v1")
        self.assertIn("mysql+pymysql://", settings.SQLALCHEMY_DATABASE_URI)

    def test_root_endpoint(self):
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("Welcome to Enterprise AI Digital Assistant", data["message"])

    def test_health_endpoint_schema(self):
        response = client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("services", data)
        self.assertIn("mysql", data["services"])
        self.assertIn("redis", data["services"])
        self.assertIn("qdrant", data["services"])


if __name__ == "__main__":
    unittest.main()
