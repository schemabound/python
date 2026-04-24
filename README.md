# schemabound-sdk

Python SDK for the [OAM (Object Agent Mapping)](https://github.com/schemabound/schemabound) framework. Connects Python applications to the OAM runtime over gRPC with SQLAlchemy model registration and all three schema modes.

## Installation

```bash
pip install schemabound-sdk
# or with uv
uv add schemabound-sdk
```

## Quick Start

```python
from schemabound_sdk import SchemaboundClient
from schemabound_sdk.v1.agent import service_pb2

client = SchemaboundClient(address="localhost:50051", api_key="your-api-key")
client.connect()

# Register as a DATA_FIRST agent (read-only, DB introspection)
client.register("my-agent", "1.0.0", service_pb2.SchemaMode.DATA_FIRST)

# Execute a query
response = client.execute_query("SELECT * FROM organizations LIMIT 10")

client.close()
```

## Schema Modes

```python
from schemabound_sdk.v1.agent import service_pb2

# DATA_FIRST — Discovery mode. Read-only. Backend introspects DB schema.
client.register("agent", "1.0", service_pb2.SchemaMode.DATA_FIRST)

# CODE_FIRST — App extension mode. Only registered models are queryable. Read-write.
client.register("agent", "1.0", service_pb2.SchemaMode.CODE_FIRST)

# HYBRID — Registered models first, introspection fallback. Read-only.
client.register("agent", "1.0", service_pb2.SchemaMode.HYBRID)
```

| Mode | Description | Access |
|------|-------------|--------|
| `DATA_FIRST` | DB introspection — no model registration needed | Read-only |
| `CODE_FIRST` | Registered models only — code-defined validation | Read-write |
| `HYBRID` | Registered models + introspection fallback | Read-only |

## SQLAlchemy Model Registration

Use `SchemaboundDeclarativeBase` as the base for your SQLAlchemy models to enable `CODE_FIRST` or `HYBRID` registration:

```python
from sqlalchemy.orm import DeclarativeBase
from schemabound_sdk import SchemaboundClient, SchemaboundDeclarativeBase
from schemabound_sdk.v1.agent import service_pb2

class Base(SchemaboundDeclarativeBase, DeclarativeBase):
    pass

class Organization(Base):
    """Tenant organization model."""
    __tablename__ = "organizations"

    id: int
    name: str
    slug: str

client = SchemaboundClient(address="localhost:50051")
client.connect()
client.register("my-agent", "1.0.0", service_pb2.SchemaMode.CODE_FIRST)
client.register_model(Organization)

# Only registered tables are queryable in CODE_FIRST mode
response = client.execute_query("SELECT * FROM organizations")
```

### Schema Constraint Mapping

`SchemaboundDeclarativeBase.to_roam_schema()` translates SQLAlchemy column constraints into restrictive JSON Schema rules for LLM tool calls.

| SQLAlchemy constraint | JSON Schema effect |
|---|---|
| `primary_key=True` | Description annotated `"Primary Key — auto-generated; omit on INSERT"`; excluded from `required` |
| `ForeignKey("table.col")` | Description annotated `"Foreign Key → table.col"` |
| `unique=True` | Description annotated `"UNIQUE — value must be unique across all rows"` |
| `Enum("a", "b", ...)` | Property emits `"enum": ["a", "b", ...]` |
| — | `"additionalProperties": False` on every table schema |

```python
from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from schemabound_sdk import SchemaboundDeclarativeBase

class Base(DeclarativeBase, SchemaboundDeclarativeBase):
    pass

class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)

class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    role: Mapped[str] = mapped_column(Enum("engineer", "manager", name="role_enum"))

schema = Employee.to_roam_schema()
# schema["parameters"]["additionalProperties"] == False
# schema["parameters"]["properties"]["department_id"]["description"] contains "departments.id"
# schema["parameters"]["properties"]["role"]["enum"] == ["engineer", "manager"]
```

## Runtime Context Headers

Attach request context before calling `execute_query`:

```python
client.query_context = {
    "organization_id": "org-123",
    "user_id": "user-456",
    "tool_name": "data-explorer",
    "tool_intent": "read",
    "domain_tags": ["identity"],
    "table_names": ["organizations"],
}
```

These map to the standard SCHEMABOUND runtime headers (`x-schemabound-organization-id`, `x-schemabound-user-id`, etc.) and are forwarded on every gRPC call.

## Testing

```bash
# Unit tests (no backend required)
pytest tests/unit/

# Integration tests (requires running OAM backend)
make grpc-start   # from repo root
pytest tests/integration/
```

## Related Packages

| Package | Description |
|---------|-------------|
| [`schemabound-sdk`](https://pypi.org/project/schemabound-sdk/) | This package |
| [`schemabound`](https://crates.io/crates/schemabound) | Rust core runtime |
| [`schemabound-proto`](https://crates.io/crates/schemabound-proto) | Shared protobuf definitions |

## License

Licensed under either of [Apache License 2.0](LICENSE-APACHE) or [MIT License](LICENSE-MIT) at your option.
