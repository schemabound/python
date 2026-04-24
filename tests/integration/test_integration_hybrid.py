import pytest

from schemabound_sdk.v1.agent import service_pb2


def test_hybrid_can_register_models(roaming_client):
    """
    GIVEN a client in HYBRID mode
    WHEN attempting to register a SQLAlchemy model
    THEN it should succeed (unlike DATA_FIRST)
    """
    from tests.conftest import UserDeclarativeBase

    roaming_client.register(
        agent_id="test-hybrid-register",
        version="0.1",
        mode=service_pb2.SchemaMode.HYBRID,
    )

    assert roaming_client.register_model(UserDeclarativeBase) is True


def test_hybrid_queries_registered_table(roaming_client, db_session, fake_user):
    """
    GIVEN a client in HYBRID mode with a registered model
    WHEN querying the registered table
    THEN it should succeed
    """
    from tests.conftest import UserDeclarativeBase

    # Setup data
    UserDeclarativeBase.save(db_session, fake_user)

    roaming_client.register(
        agent_id="test-hybrid-query-registered",
        version="0.1",
        mode=service_pb2.SchemaMode.HYBRID,
    )
    roaming_client.register_model(UserDeclarativeBase)

    query = "SELECT * FROM users"
    result = roaming_client.execute_query(query)
    assert result.status == 1
    assert result.row_count >= 1


def test_hybrid_queries_unregistered_table(roaming_client, db_session):
    """
    GIVEN a client in HYBRID mode
    WHEN querying a table (organizations) that exists in DB but is NOT registered locally
    THEN it should succeed (fallback to introspection), unlike CODE_FIRST
    """
    from tests.conftest import OrganizationDeclarativeBase

    # Create an organization (backend data existence)
    OrganizationDeclarativeBase.save(db_session, name="Shadow Corp")

    roaming_client.register(
        agent_id="test-hybrid-query-unregistered-org",
        version="0.1",
        mode=service_pb2.SchemaMode.HYBRID,
    )

    # We DO NOT call register_model(OrganizationDeclarativeBase) here

    query = "SELECT * FROM organizations"
    result = roaming_client.execute_query(query)

    # Logic check: Should pass in HYBRID, would fail in CODE_FIRST
    assert result.status == 1
    assert result.row_count >= 1


def test_hybrid_join_query(roaming_client, db_session, fake_user):
    """
    GIVEN a client in HYBRID mode
    WHEN executing a JOIN query between a registered table (users)
    AND an unregistered table (organizations)
    THEN it should succeed
    """
    from tests.conftest import OrganizationDeclarativeBase, UserDeclarativeBase

    # 1. Setup Relationship Data
    org = OrganizationDeclarativeBase.save(db_session, name="Hybrid Join Corp")

    # Assign user to org
    fake_user.organization_id = org.id
    UserDeclarativeBase.save(db_session, fake_user)

    # 2. Register Client in HYBRID mode
    roaming_client.register(
        agent_id="test-hybrid-join", version="0.1", mode=service_pb2.SchemaMode.HYBRID
    )

    # Register only Users (Organizations is left to introspection)
    roaming_client.register_model(UserDeclarativeBase)

    # 3. Execute JOIN
    query = """
        SELECT u.name, o.name 
        FROM users u 
        JOIN organizations o ON u.organization_id = o.id
        WHERE o.name = 'Hybrid Join Corp'
    """
    result = roaming_client.execute_query(query)

    assert result.status == 1
    assert result.row_count >= 1
