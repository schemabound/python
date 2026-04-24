import pytest

from schemabound_sdk.v1.agent import service_pb2


def test_data_first_valid(roaming_client, fake_user, db_session):
    """
    GIVEN a database populated with existing user data
    WHEN a client connects in DATA_FIRST mode
    AND executes a raw SQL query without local models
    THEN the query should succeed and return a valid status
    """

    from tests.conftest import UserDeclarativeBase

    UserDeclarativeBase.save(db_session, fake_user)
    req = service_pb2.ConnectRequest(
        agent_id="test-data-first",
        version="0.1",
        mode=service_pb2.SchemaMode.DATA_FIRST,
    )
    roaming_client.stub.Register(req)
    query = "SELECT id, name FROM users LIMIT 1"
    result = roaming_client.execute_query(query)

    assert result.status == 1
    assert result.row_count >= 0


def test_data_first_cannot_register_models(roaming_client):
    """
    GIVEN a client connected in DATA_FIRST mode
    WHEN attempting to register a SQLAlchemy model
    THEN it should raise a ValueError (or warning) because DATA_FIRST relies on introspection
    """
    from tests.conftest import UserDeclarativeBase

    roaming_client.register(
        agent_id="data-first-fail-register",
        version="0.1",
        mode=service_pb2.SchemaMode.DATA_FIRST,
    )

    with pytest.raises(ValueError, match="Cannot register models in DATA_FIRST mode"):
        roaming_client.register_model(UserDeclarativeBase)


def test_data_first_invalid(roaming_client):
    """
    GIVEN a database populated with no user data
    WHEN a client connects in DATA_FIRST mode
    AND executes a raw SQL query regarding a non-existent table
    THEN the query should fail and return an error status
    """

    roaming_client.register(
        agent_id="test-data-first-invalid",
        version="0.1",
        mode=service_pb2.SchemaMode.DATA_FIRST,
    )
    query = "SELECT * FROM non_existent_table"
    result = roaming_client.execute_query(query)

    assert result.status != 1
    assert "table " in result.error_message.lower()
    assert "non_existent_table" in result.error_message.lower()
    assert "does not exist in schema" in result.error_message.lower()
