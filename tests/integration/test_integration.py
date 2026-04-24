from schemabound_sdk.v1.agent import service_pb2


def test_connect_to_real_server(roaming_client):
    """
    Integration test that connects to a running SCHEMABOUND backend.
    """
    request = service_pb2.ConnectRequest(
        agent_id="python-integration-test-agent", version="0.1.0"
    )
    response = roaming_client.stub.Register(request)
    assert response.success is True
    assert len(response.session_id) > 0


def test_schema_mode_data_first(roaming_client):
    """Verify registration with DATA_FIRST mode."""
    req = service_pb2.ConnectRequest(
        agent_id="integration-test-data-first",
        version="0.2.0",
        mode=service_pb2.SchemaMode.DATA_FIRST,
    )
    resp = roaming_client.stub.Register(req)
    assert resp.success is True
    assert resp.session_id


def test_schema_mode_code_first(roaming_client):
    """Verify registration with CODE_FIRST mode."""
    req = service_pb2.ConnectRequest(
        agent_id="integration-test-code-first",
        version="0.2.0",
        mode=service_pb2.SchemaMode.CODE_FIRST,
    )
    resp = roaming_client.stub.Register(req)
    assert resp.success is True
    assert resp.session_id


def test_schema_mode_hybrid(roaming_client):
    """Verify registration with HYBRID mode."""
    req = service_pb2.ConnectRequest(
        agent_id="integration-test-hybrid",
        version="0.2.0",
        mode=service_pb2.SchemaMode.HYBRID,
    )
    resp = roaming_client.stub.Register(req)
    assert resp.success is True
    assert resp.session_id
