import pytest


def test_schema_mode_enum_exists():
    """
    TDD Phase 1 (Red): Verify SchemaMode enum exists in generated protos.
    This test SHOULD FAIL until we update the .proto and regenerate code.
    """
    try:
        from schemabound_sdk.v1.agent import service_pb2
    except ImportError:
        pytest.fail("Could not import service_pb2")

    # Verify specific enum exists and values match
    # Direct access will raise AttributeError if missing (Standard TDD behavior)
    assert service_pb2.SchemaMode
    assert service_pb2.SchemaMode.Value("DATA_FIRST") == 0
    assert service_pb2.SchemaMode.Value("CODE_FIRST") == 1
    assert service_pb2.SchemaMode.Value("HYBRID") == 2
