from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from schemabound_sdk.sql_alchemy import SchemaboundDeclarativeBase


class Base(DeclarativeBase, SchemaboundDeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    email: Mapped[str] = mapped_column(String)
    age: Mapped[int] = mapped_column(Integer, nullable=True)


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    role: Mapped[str] = mapped_column(
        Enum("engineer", "manager", "director", name="role_enum")
    )


def test_schemabound_schema_generation():
    schema = User.to_schemabound_schema()

    assert schema["name"] == "users"
    props = schema["parameters"]["properties"]

    # Check types
    assert props["name"]["type"] == "string"
    assert props["age"]["type"] == "integer"

    # Check required fields (id is PK so not required in input, age is nullable)
    required = schema["parameters"]["required"]
    assert "name" in required
    assert "email" in required
    assert "age" not in required
    assert "id" not in required


def test_additional_properties_false():
    schema = User.to_schemabound_schema()
    assert schema["parameters"].get("additionalProperties") is False


def test_pk_column_description_includes_insert_hint():
    schema = User.to_schemabound_schema()
    desc = schema["parameters"]["properties"]["id"]["description"]
    assert "omit on INSERT" in desc or "auto-generated" in desc.lower()


def test_unique_column_description_includes_unique():
    schema = Employee.to_schemabound_schema()
    desc = schema["parameters"]["properties"]["username"]["description"]
    assert "UNIQUE" in desc


def test_fk_column_description_includes_reference():
    schema = Employee.to_schemabound_schema()
    desc = schema["parameters"]["properties"]["department_id"]["description"]
    assert "departments" in desc and "id" in desc


def test_enum_column_includes_enum_values():
    schema = Employee.to_schemabound_schema()
    prop = schema["parameters"]["properties"]["role"]
    assert "enum" in prop
    assert set(prop["enum"]) == {"engineer", "manager", "director"}
