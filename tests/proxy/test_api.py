"""Test the proxy API endpoints."""

import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.proxy.api.main import app
from src.proxy.models.database import Base, get_db
from src.proxy.models import Provider, ProviderKey, ModelMapping
from src.proxy.core.encryption import encrypt_api_key

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module")
def setup_database():
    """Setup test database."""
    Base.metadata.create_all(bind=engine)
    
    # Create test data
    db = TestingSessionLocal()
    
    try:
        # Create test provider
        provider = Provider(
            name="test-openai",
            provider_type="openai",
            base_url="https://api.openai.com/v1",
            config_json={},
            status="active"
        )
        db.add(provider)
        db.commit()
        db.refresh(provider)
        
        # Create test API key
        key = ProviderKey(
            provider_id=provider.id,
            key_id="test-key-1",
            key_value_encrypted=encrypt_api_key("sk-test-key-123"),
            priority=100,
            status="active"
        )
        db.add(key)
        db.commit()
        
        # Create test model mapping
        mapping = ModelMapping(
            alias_name="gpt-3.5-turbo",
            provider_id=provider.id,
            provider_model_name="gpt-3.5-turbo",
            order_index=0
        )
        db.add(mapping)
        db.commit()
        
    finally:
        db.close()
    
    yield
    
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Test client."""
    return TestClient(app)


def test_health_endpoint(client, setup_database):
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_readyz_endpoint(client, setup_database):
    """Test readiness endpoint."""
    response = client.get("/readyz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"


def test_metrics_endpoint(client, setup_database):
    """Test metrics endpoint."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]


def test_list_models(client, setup_database):
    """Test list models endpoint."""
    response = client.get("/v1/models", headers={"Authorization": "Bearer test-key"})
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "list"
    assert len(data["data"]) > 0
    assert data["data"][0]["id"] == "gpt-3.5-turbo"


def test_chat_completion_without_auth(client, setup_database):
    """Test chat completion without authentication."""
    response = client.post("/v1/chat/completions", json={
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "Hello"}]
    })
    assert response.status_code == 401


def test_admin_endpoints_protection(client, setup_database):
    """Test that admin endpoints require authentication."""
    response = client.get("/admin/providers")
    assert response.status_code == 401


def test_invalid_model(client, setup_database):
    """Test request with invalid model."""
    response = client.post("/v1/chat/completions", 
                          headers={"Authorization": "Bearer test-key"},
                          json={
                              "model": "invalid-model",
                              "messages": [{"role": "user", "content": "Hello"}]
                          })
    assert response.status_code == 404