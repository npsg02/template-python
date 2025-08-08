#!/usr/bin/env python3
"""Database setup and initialization script."""

import asyncio
import os
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from proxy.models import Base, Provider, ProviderKey, ModelMapping, User, FallbackPolicy
from proxy.models.database import create_tables, get_db_session
from proxy.core.encryption import encrypt_api_key, generate_fernet_key
from proxy.config import settings


def create_sample_data():
    """Create sample data for testing."""
    print("Creating sample data...")
    
    with get_db_session() as db:
        # Create OpenAI provider
        openai_provider = Provider(
            name="openai-primary",
            provider_type="openai",
            base_url="https://api.openai.com/v1",
            config_json={"timeout": 30},
            status="active"
        )
        db.add(openai_provider)
        db.commit()
        db.refresh(openai_provider)
        
        # Create mock provider for testing
        mock_provider = Provider(
            name="mock-provider",
            provider_type="mock",
            base_url="http://localhost:8080",
            config_json={"simulate_delay": 0.1, "failure_rate": 0.0},
            status="active"
        )
        db.add(mock_provider)
        db.commit()
        db.refresh(mock_provider)
        
        # Create sample API keys (encrypted)
        sample_keys = [
            {
                "provider_id": openai_provider.id,
                "key_id": "openai-key-1",
                "key_value": "sk-example-key-please-replace-with-real-key",
                "priority": 100
            },
            {
                "provider_id": mock_provider.id,
                "key_id": "mock-key-1", 
                "key_value": "mock-api-key-123",
                "priority": 100
            }
        ]
        
        for key_data in sample_keys:
            encrypted_key = encrypt_api_key(key_data["key_value"])
            provider_key = ProviderKey(
                provider_id=key_data["provider_id"],
                key_id=key_data["key_id"],
                key_value_encrypted=encrypted_key,
                priority=key_data["priority"],
                status="active",
                rate_limit_rpm=1000,
                rate_limit_tpm=100000
            )
            db.add(provider_key)
        
        db.commit()
        
        # Create model mappings
        model_mappings = [
            {
                "alias_name": "gpt-3.5-turbo",
                "provider_id": openai_provider.id,
                "provider_model_name": "gpt-3.5-turbo",
                "order_index": 0,
                "is_default": True
            },
            {
                "alias_name": "gpt-3.5-turbo",
                "provider_id": mock_provider.id,
                "provider_model_name": "mock-gpt-3.5-turbo",
                "order_index": 1,
                "is_default": False
            },
            {
                "alias_name": "gpt-4",
                "provider_id": openai_provider.id,
                "provider_model_name": "gpt-4",
                "order_index": 0,
                "is_default": True
            },
            {
                "alias_name": "text-embedding-ada-002",
                "provider_id": openai_provider.id,
                "provider_model_name": "text-embedding-ada-002",
                "order_index": 0,
                "is_default": True
            }
        ]
        
        for mapping_data in model_mappings:
            model_mapping = ModelMapping(**mapping_data)
            db.add(model_mapping)
        
        db.commit()
        
        # Create default fallback policy
        default_policy = FallbackPolicy(
            name="default",
            description="Default fallback policy",
            policy_json={
                "max_attempts": 3,
                "retry_conditions": ["rate_limit", "server_error", "timeout"],
                "backoff_strategy": "exponential",
                "initial_delay": 1.0,
                "max_delay": 60.0,
                "circuit_breaker": {
                    "failure_threshold": 5,
                    "recovery_timeout": 60
                }
            },
            is_default=True,
            is_active=True
        )
        db.add(default_policy)
        
        # Create admin user
        admin_user = User(
            username="admin",
            email="admin@example.com",
            hashed_password="hashed_password_here",  # In real use, hash properly
            is_active=True,
            is_admin=True,
            api_key="admin-key-12345",  # For API access
            rate_limit_rpm=1000
        )
        db.add(admin_user)
        
        db.commit()
        
        print("Sample data created successfully!")
        print("\nCreated providers:")
        print(f"  - {openai_provider.name} ({openai_provider.provider_type})")
        print(f"  - {mock_provider.name} ({mock_provider.provider_type})")
        print("\nCreated model mappings:")
        for mapping_data in model_mappings:
            print(f"  - {mapping_data['alias_name']} -> {mapping_data['provider_model_name']}")
        print(f"\nAdmin API key: {admin_user.api_key}")


def main():
    """Main setup function."""
    print("OpenAI Proxy Database Setup")
    print("===========================")
    print(f"Database URL: {settings.database.url}")
    
    try:
        # Create tables
        print("Creating database tables...")
        create_tables()
        print("Database tables created successfully!")
        
        # Create sample data
        create_sample_data()
        
        print("\n✅ Database setup completed successfully!")
        print("\nNext steps:")
        print("1. Update the OpenAI API keys in the provider_keys table")
        print("2. Configure your .env file with proper credentials")
        print("3. Start the proxy server: python main.py")
        print("4. Test with: curl -H 'Authorization: Bearer <api-key>' http://localhost:8000/v1/models")
        
        # Show encryption key info
        print(f"\n🔐 Encryption key in use: {settings.security.encryption_key[:8]}...")
        print("   (Change this in production!)")
        
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        raise


if __name__ == "__main__":
    main()