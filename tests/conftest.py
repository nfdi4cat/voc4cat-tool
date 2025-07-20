# Common pytest fixtures for all test modules
import tempfile
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Annotated

import pytest
from pydantic import BaseModel, Field

from voc4cat.xlsx_common import XLSXMetadata


# Test Enums
class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


# Test Models
class Employee(BaseModel):
    """Test model for employee data."""

    employee_id: int
    first_name: str
    last_name: str
    email: str
    hire_date: date
    salary: float
    status: Status
    department: str | None = None
    is_active: bool = True


class Project(BaseModel):
    """Test model for project data."""

    project_id: int
    project_name: str
    start_date: date
    priority: Priority
    budget: float
    description: str | None = Field(None, description="Project description")
    end_date: date | None = None
    is_completed: bool = False


class SimpleModel(BaseModel):
    """Simple test model."""

    name: str
    value: int
    active: bool = True


class DemoModelWithMetadata(BaseModel):
    """Demo model with XLSX metadata for testing."""

    temp: Annotated[
        float,
        XLSXMetadata(
            unit="°C",
            meaning="Temperature measurement",
            description="Temperature reading",
        ),
    ]
    name: Annotated[
        str,
        XLSXMetadata(
            meaning="Sample name",
            description="Sample identifier",
        ),
    ]


@pytest.fixture(scope="session")
def datadir():
    """DATADIR as a LocalPath"""
    return Path(__file__).resolve().parent / "data"


@pytest.fixture
def temp_config():
    """
    Provides a temporary config that can be safely changed in test functions.

    After the test the config will be reset to default.
    """
    from voc4cat import config

    config.curies_converter.add_prefix("ex", "http://example.org/", merge=True)
    yield config

    # Reset the globally changed config to default.
    config.load_config()


# XLSX Testing Fixtures
@pytest.fixture
def sample_employees():
    """Sample employee data."""
    return [
        Employee(
            employee_id=1,
            first_name="John",
            last_name="Doe",
            email="john.doe@company.com",
            hire_date=date(2023, 1, 15),
            salary=75000.0,
            status=Status.ACTIVE,
            department="Engineering",
        ),
        Employee(
            employee_id=2,
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@company.com",
            hire_date=date(2023, 3, 1),
            salary=82000.0,
            status=Status.ACTIVE,
            department="Marketing",
            is_active=False,
        ),
    ]


@pytest.fixture
def sample_projects():
    """Sample project data."""
    return [
        Project(
            project_id=1,
            project_name="Website Redesign",
            description="Complete overhaul of company website",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
            priority=Priority.HIGH,
            budget=150000.0,
        ),
        Project(
            project_id=2,
            project_name="Mobile App",
            description="Mobile application development",
            start_date=date(2024, 2, 15),
            priority=Priority.MEDIUM,
            budget=200000.0,
        ),
    ]


@pytest.fixture
def sample_simple_model():
    """Sample simple model."""
    return SimpleModel(name="Test Item", value=42, active=True)


@pytest.fixture
def sample_model_with_metadata():
    """Sample model with XLSX metadata."""
    return DemoModelWithMetadata(temp=25.5, name="Test Sample")


@pytest.fixture
def temp_file():
    """Temporary file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        yield Path(f.name)
    Path(f.name).unlink(missing_ok=True)


# Additional XLSX Testing Fixtures for Optimized Testing
@pytest.fixture
def sample_employee():
    """Single employee for key-value testing."""
    return Employee(
        employee_id=1,
        first_name="John",
        last_name="Doe",
        email="john@test.com",
        hire_date=date(2023, 1, 1),
        salary=50000.0,
        status=Status.ACTIVE,
        department="Engineering",
        is_active=True,
    )


@pytest.fixture
def sample_project():
    """Single project for key-value testing."""
    return Project(
        project_id=1,
        project_name="Test Project",
        start_date=date(2024, 1, 1),
        priority=Priority.HIGH,
        budget=100000.0,
        description="Test project description",
        end_date=None,
        is_completed=False,
    )


@pytest.fixture
def xlsx_metadata_map():
    """Common XLSX metadata for Employee model."""
    return {
        "salary": XLSXMetadata(unit="USD", description="Annual salary"),
        "first_name": XLSXMetadata(description="Employee first name"),
        "hire_date": XLSXMetadata(description="Date of hire"),
    }


@pytest.fixture
def large_employee_dataset():
    """Large dataset for performance testing."""
    return [
        Employee(
            employee_id=i,
            first_name=f"Employee{i}",
            last_name=f"Lastname{i}",
            email=f"emp{i}@company.com",
            hire_date=date(2023, 1, 1),
            salary=50000.0 + (i * 1000),
            status=Status.ACTIVE if i % 2 == 0 else Status.INACTIVE,
            department=f"Dept{i % 5}",
        )
        for i in range(100)  # 100 employees
    ]
