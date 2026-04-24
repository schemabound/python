from typing import Any, Callable, Optional, Type

import grpc
from pydantic import BaseModel

from .sql_alchemy import SchemaboundDeclarativeBase

# Import generated gRPC code relative to this file
# Note: real implementation would need to handle import paths carefully
# To regenerate: python -m grpc_tools.protoc -I../../schemabound-proto/src --python_out=. --grpc_python_out=. ../../schemabound-proto/src/v1/agent/service.proto
# Then fix imports in service_pb2_grpc.py: from . import service_pb2
try:
    from .v1.agent import service_pb2, service_pb2_grpc  # type: ignore
except ImportError:
    # Use mocks/placeholders if protos are not generated yet
    service_pb2 = None
    service_pb2_grpc = None


class _APIKeyInterceptor(
    grpc.UnaryUnaryClientInterceptor,
    grpc.UnaryStreamClientInterceptor,
    grpc.StreamUnaryClientInterceptor,
    grpc.StreamStreamClientInterceptor,
):
    def __init__(self, key, value):
        self._key = key
        self._value = value

    def _intercept_call(self, continuation, client_call_details, request_iterator):
        metadata = (
            list(client_call_details.metadata) if client_call_details.metadata else []
        )
        metadata.append((self._key, self._value))

        updated_details = client_call_details._replace(metadata=metadata)
        return continuation(updated_details, request_iterator)

    def intercept_unary_unary(self, continuation, client_call_details, request):
        return self._intercept_call(continuation, client_call_details, request)

    def intercept_unary_stream(self, continuation, client_call_details, request):
        return self._intercept_call(continuation, client_call_details, request)

    def intercept_stream_unary(
        self, continuation, client_call_details, request_iterator
    ):
        return self._intercept_call(continuation, client_call_details, request_iterator)

    def intercept_stream_stream(
        self, continuation, client_call_details, request_iterator
    ):
        return self._intercept_call(continuation, client_call_details, request_iterator)


class SchemaboundClient:
    """
    Main client for interacting with the SCHEMABOUND OAM (Object Agent Mapper).
    Wrapper around the generated gRPC client.
    """

    def __init__(self, address: str = "localhost:50051", api_key: Optional[str] = None):
        self.address = address
        self.api_key = api_key
        self.channel = None
        self.stub = None
        self.connected = False
        self.mode = None
        self.session_id: Optional[str] = None
        self.registered_tables = set()
        self.query_context: dict[str, Any] = {}

    def connect(self):
        """Establishes gRPC channel."""
        base_channel = grpc.insecure_channel(self.address)

        if self.api_key:
            interceptor = _APIKeyInterceptor("x-schemabound-api-key", self.api_key)
            self.channel = grpc.intercept_channel(base_channel, interceptor)
        else:
            self.channel = base_channel

        if service_pb2_grpc:
            self.stub = service_pb2_grpc.AgentServiceStub(self.channel)
        else:
            raise ImportError(
                "gRPC stubs not found. Run 'roam proto gen' to generate python bindings."
            )
        self.connected = True
        return True

    def register(self, agent_id: str, version: str, mode: int) -> Any:
        """
        High-level wrapper to register this agent with the backend.
        Stores the SchemaMode state for local validation.
        """
        if not self.connected:
            self.connect()

        if service_pb2:
            req = service_pb2.ConnectRequest(
                agent_id=agent_id, version=version, mode=mode
            )
            # Use the stub to make the call
            resp = self.stub.Register(req)
            if resp.success:
                self.mode = mode
                self.session_id = resp.session_id
            return resp
        return None

    def set_query_context(
        self,
        *,
        organization_id: Optional[str] = None,
        user_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_intent: Optional[str] = None,
        grants: Optional[list[str]] = None,
        runtime_augmentation_id: Optional[str] = None,
        runtime_augmentation_key: Optional[str] = None,
        domain_tags: Optional[list[str]] = None,
        table_names: Optional[list[str]] = None,
    ) -> None:
        self.query_context = {
            "organization_id": organization_id,
            "user_id": user_id,
            "tool_name": tool_name,
            "tool_intent": tool_intent,
            "grants": grants or [],
            "runtime_augmentation_id": runtime_augmentation_id,
            "runtime_augmentation_key": runtime_augmentation_key,
            "domain_tags": domain_tags or [],
            "table_names": table_names or [],
        }

    def clear_query_context(self) -> None:
        self.query_context = {}

    def _query_metadata(self) -> list[tuple[str, str]]:
        metadata: list[tuple[str, str]] = []

        # TODO: Keep this metadata contract aligned across first-party SDKs so the
        # public request context behaves consistently for Python and .NET clients.
        if self.session_id:
            metadata.append(("x-schemabound-session-id", self.session_id))

        scalar_fields = {
            "x-schemabound-organization-id": self.query_context.get("organization_id"),
            "x-schemabound-user-id": self.query_context.get("user_id"),
            "x-schemabound-tool-name": self.query_context.get("tool_name"),
            "x-schemabound-tool-intent": self.query_context.get("tool_intent"),
            "x-schemabound-runtime-augmentation-id": self.query_context.get(
                "runtime_augmentation_id"
            ),
            "x-schemabound-runtime-augmentation-key": self.query_context.get(
                "runtime_augmentation_key"
            ),
        }

        for key, value in scalar_fields.items():
            if value:
                metadata.append((key, value))

        list_fields = {
            "x-schemabound-grants": self.query_context.get("grants") or [],
            "x-schemabound-domain-tags": self.query_context.get("domain_tags") or [],
            "x-schemabound-table-names": self.query_context.get("table_names") or [],
        }

        for key, values in list_fields.items():
            if values:
                metadata.append((key, ",".join(values)))

        return metadata

    def register_tool(self, tool_def: dict) -> bool:
        """
        Registers a tool definition with the OAM agent.
        """
        # In a real implementation, this would call a gRPC method
        # e.g. self.stub.RegisterTool(tool_def)
        return True

    def register_model(self, model_class: Type[SchemaboundDeclarativeBase]) -> bool:
        """
        Registers a SQLAlchemy model (with SchemaboundDeclarativeBase) with the OAM agent.
        """
        if not hasattr(model_class, "to_schemabound_schema"):
            raise ValueError("Model must inherit from SchemaboundDeclarativeBase")

        # Check for DATA_FIRST mode violation
        if self.mode is not None and service_pb2:
            if self.mode == service_pb2.SchemaMode.DATA_FIRST:
                raise ValueError(
                    "Cannot register models in DATA_FIRST mode. Use CODE_FIRST or HYBRID."
                )

        # Here we would convert the model to schema and register it
        # Keep track of registered tables for local validation
        if hasattr(model_class, "__tablename__"):
            self.registered_tables.add(model_class.__tablename__)

        # For now, just return True
        return True

    def execute_query(self, query: str, limit: int = 100) -> Any:
        """
        Executes a raw SQL query against the backend.
        Used primarily in DATA_FIRST mode.
        """
        if not self.connected:
            raise RuntimeError("Client not connected")

        # CODE_FIRST Validation (Client-side Pre-check)
        # NOTE: The authoritative validation happens on the backend.
        # This check is for immediate developer feedback (DX).
        if self.mode == service_pb2.SchemaMode.CODE_FIRST:
            import re

            # Basic extraction of table names (words after FROM or JOIN).
            # This lightweight pre-check is meant for local developer feedback only;
            # authoritative validation belongs to the service runtime.
            matches = re.finditer(
                r"(?:FROM|JOIN)\s+([a-zA-Z0-9_]+)", query, re.IGNORECASE
            )

            for match in matches:
                table_name = match.group(1)
                if table_name not in self.registered_tables:
                    raise ValueError(
                        f"Table '{table_name}' is not registered. In CODE_FIRST mode, only registered models can be queried."
                    )

        # Create the Query Service stub if not already created
        # In a real app, we might do this in connect(), but v1.query might be optional
        try:
            from .v1.query import service_pb2 as query_pb2
            from .v1.query import service_pb2_grpc as query_grpc
        except ImportError:
            raise ImportError("Query service protos not found")

        query_stub = query_grpc.QueryServiceStub(self.channel)

        req = query_pb2.ExecuteQueryRequest(
            db_identifier="default",  # In the future this could be configurable
            query=query,
            limit=limit,
        )

        try:
            response = query_stub.ExecuteQuery(req, metadata=self._query_metadata())
            return response
        except grpc.RpcError as e:
            # Handle gRPC errors (e.g. re-raise as SDK specific error)
            raise e

    def close(self):
        if self.channel:
            self.channel.close()
