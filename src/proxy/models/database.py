"""Database configuration and connection management."""

import os
from typing import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from . import Base


class DatabaseConfig:
    """Database configuration."""
    
    def __init__(self):
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/openai_proxy"
        )
        self.echo = os.getenv("DATABASE_ECHO", "false").lower() == "true"
        self.pool_size = int(os.getenv("DATABASE_POOL_SIZE", "10"))
        self.max_overflow = int(os.getenv("DATABASE_MAX_OVERFLOW", "20"))
        self.pool_pre_ping = True
        self.pool_recycle = int(os.getenv("DATABASE_POOL_RECYCLE", "3600"))


# Global database configuration
db_config = DatabaseConfig()

# Create engine
engine: Engine = create_engine(
    db_config.database_url,
    echo=db_config.echo,
    poolclass=QueuePool,
    pool_size=db_config.pool_size,
    max_overflow=db_config.max_overflow,
    pool_pre_ping=db_config.pool_pre_ping,
    pool_recycle=db_config.pool_recycle,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager to get database session."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def create_tables():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop all tables."""
    Base.metadata.drop_all(bind=engine)


def reset_database():
    """Reset database by dropping and creating all tables."""
    drop_tables()
    create_tables()