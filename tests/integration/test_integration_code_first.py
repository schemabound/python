import pytest

from schemabound_sdk.v1.agent import service_pb2


def test_code_first_valid_registration(roaming_client, db_session, fake_user):
    """
    GIVEN a client in CODE_FIRST mode
    WHEN registering a valid SQLAlchemy model
    THEN the registration should succeed locally
    """
    from tests.conftest import UserDeclarativeBase

    UserDeclarativeBase.save(db_session, fake_user)

    roaming_client.register(
        agent_id="test-code-first-valid",
        version="0.1",
        mode=service_pb2.SchemaMode.CODE_FIRST,
    )
    assert roaming_client.register_model(UserDeclarativeBase) is True
    query = "SELECT * FROM users"
    result = roaming_client.execute_query(query)

    assert result.status == 1
    assert result.row_count >= 1


def test_code_first_restricts_unknown_tables(roaming_client):
    """
    GIVEN a client in CODE_FIRST mode
    WHEN querying a table that was NOT registered via register_model
    THEN the client SDK should block the query (or the backend should)

    NOTE: Currently implementing SDK-side check for immediate feedback.
    """
    roaming_client.register(
        agent_id="test-code-first-restrict",
        version="0.1",
        mode=service_pb2.SchemaMode.CODE_FIRST,
    )
    query = "SELECT * FROM unregistered_table"

    # If we implement SDK-side checking:
    with pytest.raises(
        ValueError, match="Table 'unregistered_table' is not registered"
    ):
        roaming_client.execute_query(query)


def test_code_first_fails_mixed_join(roaming_client, db_session, fake_user):
    """
    GIVEN a client in CODE_FIRST mode
    WHEN executing a JOIN query between a registered table (users)
    AND an unregistered table (organizations)
    THEN it should FAIL (Client-side validation)
    """
    from tests.conftest import OrganizationDeclarativeBase, UserDeclarativeBase

    # Setup
    org = OrganizationDeclarativeBase.save(db_session, name="Prohibited Corp")
    fake_user.organization_id = org.id
    UserDeclarativeBase.save(db_session, fake_user)

    roaming_client.register(
        agent_id="test-code-first-join-fail",
        version="0.1",
        mode=service_pb2.SchemaMode.CODE_FIRST,
    )

    # Register Users ONLY
    roaming_client.register_model(UserDeclarativeBase)
    # Organization is NOT registered

    # Query uses "users" (valid) and "organizations" (invalid)
    query = "SELECT * FROM users JOIN organizations ON users.organization_id = organizations.id"

    # Expectation: Should fail because 'organizations' is not registered
    with pytest.raises(ValueError, match="not registered"):
        roaming_client.execute_query(query)
