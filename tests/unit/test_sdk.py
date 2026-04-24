from unittest.mock import patch

import pytest
from pydantic import BaseModel, Field

from schemabound_sdk.client import SchemaboundClient
from schemabound_sdk.decorators import wrap_tool_call
from schemabound_sdk.testing import TestClient


# Define a Pydantic model for the agent's input
class SearchInput(BaseModel):
    query: str = Field(..., description="The search query")
    limit: int = Field(10, description="Max results")


# Define a Pydantic model for the output
class SearchResult(BaseModel):
    title: str
    url: str


class SearchResponse(BaseModel):
    results: list[SearchResult]


# Mock client for testing without a real server
# Use the official TestClient from schemabound_sdk.testing


@pytest.fixture
def client():
    c = TestClient()
    c.connect()
    return c


def test_client_init(client):
    assert client.connected


def test_pydantic_integration():
    """Test that models can be used with the SDK structure"""
    input_data = SearchInput(query="rust lang", limit=5)
    assert input_data.query == "rust lang"
    assert input_data.limit == 5


def test_decorator_metadata():
    """Test that the decorator attaches OAM metadata"""

    @wrap_tool_call(name="web_search", description="Searches the web")
    def search_tool(query: str) -> str:
        return f"Results for {query}"

    # Verify metadata is attached
    assert hasattr(search_tool, "oam_tool_def")
    tool_def = search_tool.oam_tool_def
    assert tool_def["name"] == "web_search"
    assert tool_def["description"] == "Searches the web"

    # Verify execution still works
    assert search_tool("test") == "Results for test"


def test_connect_missing_stubs():
    """Test that connection fails appropriately when stubs are missing."""
    # Mock that the gRPC module is None (simulating import error)
    with patch("schemabound_sdk.client.service_pb2_grpc", None):
        client = SchemaboundClient()
        # The client should suggest running the generation command
        with pytest.raises(ImportError, match="Run 'roam proto gen'"):
            client.connect()


def test_query_metadata_includes_session_and_prompt_context():
    client = SchemaboundClient()
    client.session_id = "session-123"
    client.set_query_context(
        organization_id="finance",
        user_id="user-1",
        tool_name="finance.query",
        tool_intent="read_select",
        grants=["read:ledger", "read:org"],
        runtime_augmentation_id="hook-1",
        runtime_augmentation_key="finance-default",
        domain_tags=["finance", "accounting"],
        table_names=["ledger_entries", "organizations"],
    )

    metadata = dict(client._query_metadata())

    assert metadata["x-schemabound-session-id"] == "session-123"
    assert metadata["x-schemabound-organization-id"] == "finance"
    assert metadata["x-schemabound-user-id"] == "user-1"
    assert metadata["x-schemabound-tool-name"] == "finance.query"
    assert metadata["x-schemabound-tool-intent"] == "read_select"
    assert metadata["x-schemabound-grants"] == "read:ledger,read:org"
    assert metadata["x-schemabound-runtime-augmentation-id"] == "hook-1"
    assert metadata["x-schemabound-runtime-augmentation-key"] == "finance-default"
    assert metadata["x-schemabound-domain-tags"] == "finance,accounting"
    assert metadata["x-schemabound-table-names"] == "ledger_entries,organizations"
