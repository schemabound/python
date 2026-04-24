import os

import pytest
from faker import Faker
from pydantic import BaseModel, EmailStr
from sqlalchemy import Boolean, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)

from schemabound_sdk.client import SchemaboundClient
from schemabound_sdk.sql_alchemy import SchemaboundDeclarativeBase


# --- PyDantic Model (The "UserBaseModel") ---
class UserBaseModel(BaseModel):
    name: str
    email: EmailStr
    age: int
    is_active: bool = True
    organization_id: int | None = None


# --- SQLAlchemy Model (The "UserDeclarativeBase") ---
class Base(DeclarativeBase, SchemaboundDeclarativeBase):
    pass


class OrganizationDeclarativeBase(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)

    # Relationship
    users = relationship("UserDeclarativeBase", back_populates="organization")

    @classmethod
    def save(cls, session, name: str) -> "OrganizationDeclarativeBase":
        org = cls(name=name)
        session.add(org)
        session.commit()
        session.refresh(org)
        return org


class UserDeclarativeBase(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, unique=True)
    age: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"))
    organization = relationship("OrganizationDeclarativeBase", back_populates="users")

    @classmethod
    def save(cls, session, user_data: UserBaseModel) -> "UserDeclarativeBase":
        """Saves a Pydantic model to the DB via SQLAlchemy."""
        db_user = cls(**user_data.model_dump())
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        return db_user

    @classmethod
    def list(cls, session) -> list["UserDeclarativeBase"]:
        """Lists all users."""
        return session.query(cls).all()


# --- Fixtures ---


@pytest.fixture(scope="session")
def roaming_client():
    """Fixture that provides a connected SchemaboundClient for the entire test session."""
    address = os.getenv("SCHEMABOUND_TEST_GRPC_ADDR", "localhost:50051")
    api_key = os.getenv("SCHEMABOUND_API_KEY", "test-api-key")

    print(f"Connecting to SCHEMABOUND Backend at {address}...")
    client = SchemaboundClient(address=address, api_key=api_key)
    client.connect()
    yield client
    client.channel.close()


@pytest.fixture(scope="session")
def fake():
    """Session-scoped Faker instance."""
    return Faker()


@pytest.fixture
def fake_user(fake):
    """Generates a Pydantic UserBaseModel with fake data."""
    return UserBaseModel(
        name=fake.name(),
        email=fake.email(),
        age=fake.random_int(min=18, max=90),
        is_active=True,
    )


@pytest.fixture(scope="session")
def db_session_factory():
    """
    Session-scoped database engine and session factory.
    Ideally, this would connect to the same Dolt database SCHEMABOUND is using.

    NOTE: The current 'make test' infrastructure launches a lightweight 'schemabound-grpc-server'
    that uses a local SQLite file (/tmp/roam_test.db). To ensure our integration
    tests see the same data as the backend, we connect to that SQLite file.

    If running against the full 'services/backend' with 'make local', we would use Dolt.
    """
    # Check if we are running in CI/Test mode against the lightweight backend
    roam_db_path = os.getenv("SCHEMABOUND_DB_PATH", "/tmp/roam_test.db")

    # Use SQLite by default for now to match the current test runner
    db_url = f"sqlite:///{roam_db_path}"

    # Allow override for Dolt if explicitly requested
    if os.getenv("SCHEMABOUND_TEST_USE_DOLT"):
        db_url = os.getenv(
            "SCHEMABOUND_TEST_DB_URL", "mysql+mysqlconnector://root@127.0.0.1:3307/schemabound_dev"
        )

    try:
        engine = create_engine(db_url)
        # Create tables
        Base.metadata.create_all(engine)
    except Exception as e:
        print(
            f"Warning: Could not connect to {db_url}: {e}, falling back to in-memory SQLite"
        )
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    return Session


@pytest.fixture
def db_session(db_session_factory):
    """Function-scoped database session."""
    session = db_session_factory()
    yield session
    session.close()
