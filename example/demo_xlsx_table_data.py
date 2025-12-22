#!/usr/bin/env python3
"""
Demo: Table Data Representations and Serialization

This demo focuses on data representations, joins, and serialization for table format.
It demonstrates how to handle complex data structures and convert between Python
types and Excel-compatible formats.

Features demonstrated:
- Table format for multiple records
- Built-in converters (comma, pipe, semicolon separators)
- Custom serializers for dates and enums
- List to pipe conversion
- Round-trip data integrity
- Auto-detection for table format
- Model joins for flattening nested data
"""

import sys
import traceback
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field

from voc4cat.xlsx_api import XLSXProcessorFactory, export_to_xlsx, import_from_xlsx
from voc4cat.xlsx_common import (
    MetadataToggleConfig,
    MetadataVisibility,
    XLSXConverters,
    XLSXMetadata,
)
from voc4cat.xlsx_table import JoinConfiguration, XLSXTableConfig


# Enums for validation
class Department(Enum):
    ENGINEERING = "engineering"
    MARKETING = "marketing"
    SALES = "sales"
    HR = "human_resources"


class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Custom serializers
def custom_date_serializer(value: date) -> str:
    """Custom serializer for dates in DD/MM/YYYY format."""
    return value.strftime("%d/%m/%Y")


def custom_date_deserializer(value: str) -> date:
    """Custom deserializer for dates from DD/MM/YYYY format."""

    return datetime.strptime(value, "%d/%m/%Y").date()  # noqa: DTZ007


def custom_priority_serializer(value: Priority) -> str:
    """Custom serializer for priority enum with emojis."""
    emoji_map = {
        Priority.LOW: "🟢 Low",
        Priority.MEDIUM: "🟡 Medium",
        Priority.HIGH: "🔴 High",
    }
    return emoji_map.get(value, str(value.value))


def custom_priority_deserializer(value: str) -> Priority:
    """Custom deserializer for priority enum from emoji format."""
    clean_value = value.split()[-1].lower() if value else "medium"
    value_map = {"low": Priority.LOW, "medium": Priority.MEDIUM, "high": Priority.HIGH}
    return value_map.get(clean_value, Priority.MEDIUM)


# Models
class Employee(BaseModel):
    """Employee model for basic table format demonstration."""

    employee_id: int = Field(..., description="Unique employee identifier")
    first_name: str = Field(..., description="Employee's first name")
    last_name: str = Field(..., description="Employee's last name")
    email: str = Field(..., description="Work email address")
    department: Department = Field(..., description="Employee's department")
    hire_date: date = Field(..., description="Date of hire")
    salary: float = Field(..., description="Annual salary in USD")
    status: Status = Field(default=Status.ACTIVE, description="Employment status")
    is_manager: bool = Field(default=False, description="Whether employee is a manager")


class Task(BaseModel):
    """Task model demonstrating built-in converters."""

    task_id: int = Field(..., description="Unique task identifier")
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Task description")

    # Built-in converter fields
    tags: Annotated[
        list[str],
        XLSXMetadata(
            description="Task tags (comma-separated)",
            separator_pattern=XLSXConverters.COMMA,
        ),
    ] = []

    assigned_to: Annotated[
        list[str],
        XLSXMetadata(
            description="Assigned employees (pipe-separated)",
            separator_pattern=XLSXConverters.PIPE,
        ),
    ] = []

    dependencies: Annotated[
        list[str],
        XLSXMetadata(
            description="Task dependencies (semicolon-separated)",
            separator_pattern=XLSXConverters.SEMICOLON,
        ),
    ] = []

    estimated_hours: Annotated[
        list[int],
        XLSXMetadata(
            description="Estimated hours per phase (comma-separated integers)",
            xlsx_serializer=lambda x: ", ".join(str(i) for i in x) if x else "",
            xlsx_deserializer=lambda x: [
                int(i.strip()) for i in x.split(",") if i.strip()
            ]
            if x.strip()
            else [],
        ),
    ] = []

    metadata: Annotated[
        dict,
        XLSXMetadata(
            description="Task metadata (JSON)",
            xlsx_serializer=XLSXConverters.dict_to_json_string,
            xlsx_deserializer=XLSXConverters.json_string_to_dict,
        ),
    ] = {}


class ProjectWithCustomSerializers(BaseModel):
    """Project model demonstrating custom serializers."""

    project_id: int = Field(..., description="Unique project identifier")
    name: str = Field(..., description="Project name")
    description: str = Field(..., description="Project description")

    # Custom date serializer
    start_date: Annotated[
        date,
        XLSXMetadata(
            description="Project start date (DD/MM/YYYY format)",
            xlsx_serializer=custom_date_serializer,
            xlsx_deserializer=custom_date_deserializer,
        ),
    ]

    # Custom priority serializer with emojis
    priority: Annotated[
        Priority,
        XLSXMetadata(
            description="Project priority with emoji indicators",
            xlsx_serializer=custom_priority_serializer,
            xlsx_deserializer=custom_priority_deserializer,
        ),
    ] = Priority.MEDIUM

    budget: float = Field(..., description="Project budget in USD")

    # Combine custom and built-in converters
    technologies: Annotated[
        list[str],
        XLSXMetadata(
            description="Technologies used (comma-separated)",
            separator_pattern=XLSXConverters.COMMA,
        ),
    ] = []


# Models for joins demonstration
class Address(BaseModel):
    """Address model for nested data."""

    street: str = Field(..., description="Street address")
    city: str = Field(..., description="City")
    state: str = Field(..., description="State/Province")
    postal_code: str = Field(..., description="Postal code")
    country: str = Field(..., description="Country")


class Contact(BaseModel):
    """Contact model for nested data."""

    phone: str = Field(..., description="Phone number")
    email: str = Field(..., description="Email address")
    emergency_contact: str = Field(..., description="Emergency contact name")
    emergency_phone: str = Field(..., description="Emergency contact phone")


class EmployeeWithNested(BaseModel):
    """Employee model with nested data for joins demonstration."""

    employee_id: int = Field(..., description="Unique employee identifier")
    first_name: str = Field(..., description="Employee's first name")
    last_name: str = Field(..., description="Employee's last name")
    department: Department = Field(..., description="Employee's department")
    hire_date: date = Field(..., description="Date of hire")
    salary: float = Field(..., description="Annual salary in USD")

    # Nested models
    address: Address = Field(..., description="Employee address")
    contact: Contact = Field(..., description="Employee contact information")


class EmployeeJoined(BaseModel):
    """Flattened employee model for joined format."""

    employee_id: int = Field(..., description="Unique employee identifier")
    first_name: str = Field(..., description="Employee's first name")
    last_name: str = Field(..., description="Employee's last name")
    department: Department = Field(..., description="Employee's department")
    hire_date: date = Field(..., description="Date of hire")
    salary: float = Field(..., description="Annual salary in USD")

    # Flattened address fields
    address_street: str = Field(..., description="Street address")
    address_city: str = Field(..., description="City")
    address_state: str = Field(..., description="State/Province")
    address_postal_code: str = Field(..., description="Postal code")
    address_country: str = Field(..., description="Country")

    # Flattened contact fields
    contact_phone: str = Field(..., description="Phone number")
    contact_email: str = Field(..., description="Email address")
    contact_emergency_contact: str = Field(..., description="Emergency contact name")
    contact_emergency_phone: str = Field(..., description="Emergency contact phone")


# Models for multi-row joins demonstration
class Skill(BaseModel):
    """Individual skill record for multi-row joins."""

    employee_id: int = Field(..., description="Employee identifier")
    skill_name: str = Field(..., description="Name of the skill")
    proficiency_level: str = Field(
        ..., description="Proficiency level (Beginner, Intermediate, Advanced, Expert)"
    )
    years_experience: int = Field(
        ..., description="Years of experience with this skill"
    )
    certification: str | None = Field(
        None, description="Certification name if applicable"
    )
    last_used: date = Field(..., description="Date when skill was last used")


class EmployeeWithSkills(BaseModel):
    """Employee model with skills for multi-row joins demonstration."""

    employee_id: int = Field(..., description="Unique employee identifier")
    first_name: str = Field(..., description="Employee's first name")
    last_name: str = Field(..., description="Employee's last name")
    department: Department = Field(..., description="Employee's department")
    hire_date: date = Field(..., description="Date of hire")
    salary: float = Field(..., description="Annual salary in USD")

    # Skills will be joined as multiple rows
    skills: list[Skill] = Field(default_factory=list, description="Employee skills")


def create_sample_data():
    """Create sample data for demonstrations."""

    # Sample employees
    employees = [
        Employee(
            employee_id=1,
            first_name="Alice",
            last_name="Johnson",
            email="alice.johnson@company.com",
            department=Department.ENGINEERING,
            hire_date=date(2022, 1, 15),
            salary=85000.0,
            status=Status.ACTIVE,
            is_manager=True,
        ),
        Employee(
            employee_id=2,
            first_name="Bob",
            last_name="Smith",
            email="bob.smith@company.com",
            department=Department.MARKETING,
            hire_date=date(2022, 3, 10),
            salary=65000.0,
            status=Status.ACTIVE,
            is_manager=False,
        ),
        Employee(
            employee_id=3,
            first_name="Carol",
            last_name="Davis",
            email="carol.davis@company.com",
            department=Department.SALES,
            hire_date=date(2021, 8, 20),
            salary=70000.0,
            status=Status.INACTIVE,
            is_manager=False,
        ),
    ]

    # Sample employees with nested data for joins
    employees_with_nested = [
        EmployeeWithNested(
            employee_id=1,
            first_name="Alice",
            last_name="Johnson",
            department=Department.ENGINEERING,
            hire_date=date(2022, 1, 15),
            salary=85000.0,
            address=Address(
                street="123 Main St",
                city="San Francisco",
                state="CA",
                postal_code="94105",
                country="USA",
            ),
            contact=Contact(
                phone="555-0101",
                email="alice.johnson@company.com",
                emergency_contact="John Johnson",
                emergency_phone="555-0102",
            ),
        ),
        EmployeeWithNested(
            employee_id=2,
            first_name="Bob",
            last_name="Smith",
            department=Department.MARKETING,
            hire_date=date(2022, 3, 10),
            salary=65000.0,
            address=Address(
                street="456 Oak Ave",
                city="Los Angeles",
                state="CA",
                postal_code="90210",
                country="USA",
            ),
            contact=Contact(
                phone="555-0201",
                email="bob.smith@company.com",
                emergency_contact="Jane Smith",
                emergency_phone="555-0202",
            ),
        ),
    ]

    # Sample tasks with built-in converters
    tasks = [
        Task(
            task_id=1,
            title="Implement user authentication",
            description="Add OAuth2 authentication to the application",
            tags=["security", "authentication", "backend"],
            assigned_to=["alice.johnson@company.com", "bob.smith@company.com"],
            dependencies=["setup-database", "configure-oauth"],
            estimated_hours=[8, 12, 4],
            metadata={"priority_score": 85, "client_facing": True},
        ),
        Task(
            task_id=2,
            title="Design user interface",
            description="Create responsive UI components",
            tags=["ui", "frontend", "design"],
            assigned_to=["carol.davis@company.com"],
            dependencies=["wireframes"],
            estimated_hours=[16, 8],
            metadata={"priority_score": 70, "client_facing": True},
        ),
    ]

    # Sample projects with custom serializers
    projects = [
        ProjectWithCustomSerializers(
            project_id=1,
            name="E-commerce Platform",
            description="Modern e-commerce solution with advanced features",
            start_date=date(2024, 1, 15),
            priority=Priority.HIGH,
            budget=250000.0,
            technologies=["React", "Node.js", "PostgreSQL", "AWS"],
        ),
        ProjectWithCustomSerializers(
            project_id=2,
            name="Mobile App",
            description="Cross-platform mobile application",
            start_date=date(2024, 3, 1),
            priority=Priority.MEDIUM,
            budget=150000.0,
            technologies=["React Native", "Firebase", "Redux"],
        ),
    ]

    # Sample employees with skills for multi-row joins
    employees_with_skills = [
        EmployeeWithSkills(
            employee_id=1,
            first_name="Alice",
            last_name="Johnson",
            department=Department.ENGINEERING,
            hire_date=date(2022, 1, 15),
            salary=85000.0,
            skills=[
                Skill(
                    employee_id=1,
                    skill_name="Python",
                    proficiency_level="Expert",
                    years_experience=5,
                    certification="Python Institute PCAP",
                    last_used=date(2024, 1, 10),
                ),
                Skill(
                    employee_id=1,
                    skill_name="JavaScript",
                    proficiency_level="Advanced",
                    years_experience=4,
                    certification=None,
                    last_used=date(2024, 1, 8),
                ),
                Skill(
                    employee_id=1,
                    skill_name="Docker",
                    proficiency_level="Intermediate",
                    years_experience=2,
                    certification="Docker Certified Associate",
                    last_used=date(2024, 1, 5),
                ),
            ],
        ),
        EmployeeWithSkills(
            employee_id=2,
            first_name="Bob",
            last_name="Smith",
            department=Department.MARKETING,
            hire_date=date(2022, 3, 10),
            salary=65000.0,
            skills=[
                Skill(
                    employee_id=2,
                    skill_name="Google Analytics",
                    proficiency_level="Expert",
                    years_experience=3,
                    certification="Google Analytics Certified",
                    last_used=date(2024, 1, 12),
                ),
                Skill(
                    employee_id=2,
                    skill_name="Social Media Marketing",
                    proficiency_level="Advanced",
                    years_experience=4,
                    certification="HubSpot Social Media Certification",
                    last_used=date(2024, 1, 11),
                ),
            ],
        ),
        EmployeeWithSkills(
            employee_id=3,
            first_name="Carol",
            last_name="Davis",
            department=Department.SALES,
            hire_date=date(2021, 8, 20),
            salary=70000.0,
            skills=[
                Skill(
                    employee_id=3,
                    skill_name="Salesforce",
                    proficiency_level="Expert",
                    years_experience=6,
                    certification="Salesforce Administrator",
                    last_used=date(2024, 1, 9),
                ),
                Skill(
                    employee_id=3,
                    skill_name="Negotiation",
                    proficiency_level="Advanced",
                    years_experience=8,
                    certification="Harvard Negotiation Project",
                    last_used=date(2024, 1, 10),
                ),
                Skill(
                    employee_id=3,
                    skill_name="Customer Relationship Management",
                    proficiency_level="Expert",
                    years_experience=7,
                    certification=None,
                    last_used=date(2024, 1, 7),
                ),
            ],
        ),
    ]

    return employees, tasks, projects, employees_with_nested, employees_with_skills


def demo_basic_table_format(demo_file: Path):
    """Demonstrate basic table format with auto-detection."""

    print("\n" + "=" * 50)
    print("1. Basic Table Format")
    print("=" * 50)

    employees, _, _, _, _ = create_sample_data()

    # Basic export with auto-detection
    sheet_name = "Employees_Basic"
    export_to_xlsx(employees, demo_file, sheet_name=sheet_name)
    print(f"✓ Exported {len(employees)} employees to '{sheet_name}'")

    # Import back
    imported_employees = import_from_xlsx(demo_file, Employee, sheet_name=sheet_name)
    print(f"✓ Imported {len(imported_employees)} employees")

    # Verify data integrity
    for orig, imported in zip(employees, imported_employees):
        assert orig.employee_id == imported.employee_id
        assert orig.first_name == imported.first_name
        assert orig.department == imported.department
        assert orig.hire_date == imported.hire_date
    print("✓ Data integrity verified")


def demo_builtin_converters(demo_file: Path):
    """Demonstrate built-in converters for lists and dicts."""

    print("\n" + "=" * 50)
    print("2. Built-in Converters")
    print("=" * 50)

    _, tasks, _, _, _ = create_sample_data()

    # Show original data
    print("Original data:")
    for task in tasks[:1]:  # Show first task
        print(f"  - tags: {task.tags} (type: {type(task.tags)})")
        print(f"  - assigned_to: {task.assigned_to} (type: {type(task.assigned_to)})")
        print(
            f"  - dependencies: {task.dependencies} (type: {type(task.dependencies)})"
        )
        print(
            f"  - estimated_hours: {task.estimated_hours} (type: {type(task.estimated_hours)})"
        )
        print(f"  - metadata: {task.metadata} (type: {type(task.metadata)})")

    # Export with automatic conversion
    sheet_name = "Tasks_Converters"
    export_to_xlsx(tasks, demo_file, sheet_name=sheet_name)
    print(f"✓ Exported {len(tasks)} tasks with built-in converters")

    # Import back
    imported_tasks = import_from_xlsx(demo_file, Task, sheet_name=sheet_name)
    print(f"✓ Imported {len(imported_tasks)} tasks")

    # Show imported data
    print("Imported data:")
    for task in imported_tasks[:1]:  # Show first task
        print(f"  - tags: {task.tags} (type: {type(task.tags)})")
        print(f"  - assigned_to: {task.assigned_to} (type: {type(task.assigned_to)})")
        print(
            f"  - dependencies: {task.dependencies} (type: {type(task.dependencies)})"
        )
        print(
            f"  - estimated_hours: {task.estimated_hours} (type: {type(task.estimated_hours)})"
        )
        print(f"  - metadata: {task.metadata} (type: {type(task.metadata)})")

    # Verify round-trip conversion
    for orig, imported in zip(tasks, imported_tasks):
        assert orig.tags == imported.tags
        assert orig.assigned_to == imported.assigned_to
        assert orig.dependencies == imported.dependencies
        assert orig.estimated_hours == imported.estimated_hours
        assert orig.metadata == imported.metadata
    print("✓ Round-trip conversion verified")


def demo_custom_serializers(demo_file: Path):
    """Demonstrate custom field serializers."""

    print("\n" + "=" * 50)
    print("3. Custom Serializers")
    print("=" * 50)

    _, _, projects, _, _ = create_sample_data()

    # Show original data
    print("Original data:")
    for project in projects[:1]:  # Show first project
        print(
            f"  - start_date: {project.start_date} (type: {type(project.start_date)})"
        )
        print(f"  - priority: {project.priority} (type: {type(project.priority)})")
        print(
            f"  - technologies: {project.technologies} (type: {type(project.technologies)})"
        )

    # Export with custom serializers
    sheet_name = "Projects_Custom"
    export_to_xlsx(projects, demo_file, sheet_name=sheet_name)
    print(f"✓ Exported {len(projects)} projects with custom serializers")
    print("  - Dates will appear in DD/MM/YYYY format")
    print("  - Priority will appear with emoji indicators")

    # Import back
    imported_projects = import_from_xlsx(
        demo_file, ProjectWithCustomSerializers, sheet_name=sheet_name
    )
    print(f"✓ Imported {len(imported_projects)} projects")

    # Show imported data
    print("Imported data:")
    for project in imported_projects[:1]:  # Show first project
        print(
            f"  - start_date: {project.start_date} (type: {type(project.start_date)})"
        )
        print(f"  - priority: {project.priority} (type: {type(project.priority)})")
        print(
            f"  - technologies: {project.technologies} (type: {type(project.technologies)})"
        )

    # Verify round-trip conversion
    for orig, imported in zip(projects, imported_projects):
        assert orig.start_date == imported.start_date
        assert orig.priority == imported.priority
        assert orig.technologies == imported.technologies
    print("✓ Custom serializer round-trip verified")


def demo_list_to_pipe_conversion(demo_file: Path):
    """Demonstrate manual list to pipe-separated string conversion."""

    print("\n" + "=" * 50)
    print("4. List to Pipe Conversion")
    print("=" * 50)

    # Example: Manual conversion for systems that need pipe-separated strings
    skills_list = ["Python", "JavaScript", "Docker", "Kubernetes", "PostgreSQL"]
    skills_pipe = "|".join(skills_list)

    print(f"Original list: {skills_list}")
    print(f"Pipe-separated: {skills_pipe}")

    # Create a simple model to demonstrate
    class SkillRecord(BaseModel):
        record_id: int
        employee_name: str
        skills_pipe_separated: str

    records = [
        SkillRecord(
            record_id=1,
            employee_name="Alice Johnson",
            skills_pipe_separated=skills_pipe,
        ),
        SkillRecord(
            record_id=2,
            employee_name="Bob Smith",
            skills_pipe_separated="React|Node.js|MongoDB",
        ),
    ]

    # Export
    sheet_name = "Skills_Pipe"
    export_to_xlsx(records, demo_file, sheet_name=sheet_name)
    print(f"✓ Exported {len(records)} skill records")

    # Import back
    imported_records = import_from_xlsx(demo_file, SkillRecord, sheet_name=sheet_name)
    print(f"✓ Imported {len(imported_records)} records")

    # Convert back to list
    for record in imported_records:
        skills_back_to_list = record.skills_pipe_separated.split("|")
        print(f"  - {record.employee_name}: {skills_back_to_list}")

    # Verify first record
    first_imported = imported_records[0]
    imported_skills_list = first_imported.skills_pipe_separated.split("|")
    assert skills_list == imported_skills_list
    print("✓ List ↔ pipe-separated conversion verified")


def demo_model_joins(demo_file: Path):
    """Demonstrate model joins for flattening nested data."""

    print("\n" + "=" * 50)
    print("5. Model Joins for Flattening Nested Data")
    print("=" * 50)

    _, _, _, employees_with_nested, _ = create_sample_data()

    # Helper function to flatten nested employee data
    def flatten_employee(emp: EmployeeWithNested) -> EmployeeJoined:
        """Flatten nested employee data into joined format."""
        return EmployeeJoined(
            employee_id=emp.employee_id,
            first_name=emp.first_name,
            last_name=emp.last_name,
            department=emp.department,
            hire_date=emp.hire_date,
            salary=emp.salary,
            # Flatten address
            address_street=emp.address.street,
            address_city=emp.address.city,
            address_state=emp.address.state,
            address_postal_code=emp.address.postal_code,
            address_country=emp.address.country,
            # Flatten contact
            contact_phone=emp.contact.phone,
            contact_email=emp.contact.email,
            contact_emergency_contact=emp.contact.emergency_contact,
            contact_emergency_phone=emp.contact.emergency_phone,
        )

    # Show original nested structure
    print("Original nested data structure:")
    for emp in employees_with_nested[:1]:  # Show first employee
        print(f"  - {emp.first_name} {emp.last_name}:")
        print(
            f"    Address: {emp.address.street}, {emp.address.city}, {emp.address.state}"
        )
        print(f"    Contact: {emp.contact.phone}, {emp.contact.email}")
        print(
            f"    Emergency: {emp.contact.emergency_contact}, {emp.contact.emergency_phone}"
        )

    # Flatten the data
    employees_joined = [flatten_employee(emp) for emp in employees_with_nested]

    # Export flattened data
    sheet_name = "Employees_Joined"

    config = XLSXTableConfig(
        title="Employee Information (Joined Format)",
        field_order=[
            "employee_id",
            "first_name",
            "last_name",
            "department",
            "hire_date",
            "salary",
            "address_street",
            "address_city",
            "address_state",
            "address_postal_code",
            "address_country",
            "contact_phone",
            "contact_email",
            "contact_emergency_contact",
            "contact_emergency_phone",
        ],
        auto_filter=True,
    )

    export_to_xlsx(
        employees_joined,
        demo_file,
        format_type="table",
        config=config,
        sheet_name=sheet_name,
    )
    print(f"✓ Exported {len(employees_joined)} employees in joined format")
    print("  - Nested Address and Contact models flattened into columns")
    print("  - Field ordering groups related fields together")
    print("  - All data accessible in single table view")

    # Import back
    imported_joined = import_from_xlsx(
        demo_file,
        EmployeeJoined,
        format_type="table",
        config=config,
        sheet_name=sheet_name,
    )
    print(f"✓ Imported {len(imported_joined)} employees from joined format")

    # Show flattened structure
    print("Flattened data structure:")
    for emp in imported_joined[:1]:  # Show first employee
        print(f"  - {emp.first_name} {emp.last_name}:")
        print(
            f"    Address: {emp.address_street}, {emp.address_city}, {emp.address_state}"
        )
        print(f"    Contact: {emp.contact_phone}, {emp.contact_email}")
        print(
            f"    Emergency: {emp.contact_emergency_contact}, {emp.contact_emergency_phone}"
        )

    # Verify data integrity
    for orig, imported in zip(employees_joined, imported_joined):
        assert orig.employee_id == imported.employee_id
        assert orig.first_name == imported.first_name
        assert orig.address_street == imported.address_street
        assert orig.contact_phone == imported.contact_phone
    print("✓ Data integrity verified for joined format")


def demo_multi_row_joins(demo_file: Path):
    """Demonstrate multi-row joins where related data creates multiple rows."""

    print("\n" + "=" * 50)
    print("6. Multi-Row Joins (Multiple Rows per Record)")
    print("=" * 50)

    _, _, _, _, employees_with_skills = create_sample_data()

    # Show original nested structure
    print("Original nested data structure:")
    for emp in employees_with_skills[:1]:  # Show first employee
        print(f"  - {emp.first_name} {emp.last_name} ({len(emp.skills)} skills):")
        for skill in emp.skills:
            print(
                f"    • {skill.skill_name} ({skill.proficiency_level}, {skill.years_experience} years)"
            )

    # Configure the join between Employee and Skills
    join_config = JoinConfiguration(
        primary_model=EmployeeWithSkills,
        related_models={"skills": Skill},
        join_keys={"skills": "employee_id"},
        flattened_fields=[
            "employee_id",
            "first_name",
            "last_name",
            "department",
            "hire_date",
            "salary",
            "skill_name",
            "proficiency_level",
            "years_experience",
            "certification",
            "last_used",
        ],
        field_mappings={
            "employee_id": ("primary", "employee_id"),
            "first_name": ("primary", "first_name"),
            "last_name": ("primary", "last_name"),
            "department": ("primary", "department"),
            "hire_date": ("primary", "hire_date"),
            "salary": ("primary", "salary"),
            "skill_name": ("related", "skill_name"),
            "proficiency_level": ("related", "proficiency_level"),
            "years_experience": ("related", "years_experience"),
            "certification": ("related", "certification"),
            "last_used": ("related", "last_used"),
        },
        list_fields=set(),  # No list fields in this join
    )

    # Configure the joined table
    skills_config = XLSXTableConfig(
        title="Employee Skills (Multi-Row Join)",
        field_order=[
            "employee_id",
            "first_name",
            "last_name",
            "department",
            "hire_date",
            "salary",
            "skill_name",
            "proficiency_level",
            "years_experience",
            "certification",
            "last_used",
        ],
        auto_filter=True,
    )

    # Create the joined table processor
    joined_processor = XLSXProcessorFactory.create_joined_table_processor(
        join_config, skills_config
    )

    # Export using the joined processor
    sheet_name = "Employee_Skills_MultiRow"
    joined_processor.export(employees_with_skills, demo_file, sheet_name)

    print(f"✓ Exported employee skills with multi-row joins to '{sheet_name}'")
    print("  - Each employee appears in multiple rows (one per skill)")
    print("  - Employee data is repeated for each skill row")
    print("  - Creates a flat table from hierarchical data")
    print("  - Useful for database-style analysis and reporting")

    # Show how many rows were created
    total_skills = sum(len(emp.skills) for emp in employees_with_skills)
    print(
        f"  - {len(employees_with_skills)} employees with {total_skills} total skills"
    )
    print(f"  - Results in {total_skills} rows in the Excel table")

    # Note: Import back would require custom logic to reconstruct the nested structure
    # This is typically used for export/reporting scenarios rather than round-trip
    print("  - Multi-row joins are primarily used for reporting and analysis")
    print("  - Round-trip import would require custom logic to reconstruct hierarchy")


def demo_auto_detection(demo_file: Path):
    """Demonstrate automatic format detection for table data."""

    print("\n" + "=" * 50)
    print("7. Auto-Detection for Table Format")
    print("=" * 50)

    employees, _, _, _, _ = create_sample_data()

    # Test with different collection types that should all detect table format
    print("Testing table auto-detection with different collection types:")

    # List auto-detection
    sheet_name = "Auto_List"
    export_to_xlsx(employees, demo_file, sheet_name=sheet_name)  # Should detect table
    imported = import_from_xlsx(demo_file, Employee, sheet_name=sheet_name)
    print(f"✓ List: Auto-detected table format - {len(imported)} records")

    # Tuple auto-detection
    sheet_name = "Auto_Tuple"
    employees_tuple = tuple(employees[:2])
    export_to_xlsx(
        employees_tuple, demo_file, sheet_name=sheet_name
    )  # Should detect table
    imported = import_from_xlsx(demo_file, Employee, sheet_name=sheet_name)
    print(f"✓ Tuple: Auto-detected table format - {len(imported)} records")

    # Explicit format specification
    sheet_name = "Explicit_Table"
    export_to_xlsx(employees[:2], demo_file, format_type="table", sheet_name=sheet_name)
    imported = import_from_xlsx(
        demo_file, Employee, format_type="table", sheet_name=sheet_name
    )
    print(f"✓ Explicit table format: {len(imported)} records")

    print("  - Multiple collection types automatically detected as table format")
    print("  - Explicit format specification also supported")
    print("  - Consistent table layout across different input types")


def demo_requiredness_row(demo_file: Path):
    """Demonstrate requiredness row display in table format."""

    print("\n" + "=" * 50)
    print("8. Requiredness Row Display")
    print("=" * 50)

    # Model with various field types
    class ProductModel(BaseModel):
        sku: str  # Required (no default)
        name: str  # Required (no default)
        price: float = 0.0  # Optional with trivial default
        category: str = "General"  # Optional with non-trivial default
        description: str | None = None  # Optional (nullable)

    products = [
        ProductModel(sku="A001", name="Widget"),
        ProductModel(sku="A002", name="Gadget", price=19.99, category="Electronics"),
    ]

    # Export with requiredness row enabled
    config = XLSXTableConfig(
        title="Products with Requiredness",
        metadata_visibility=MetadataToggleConfig(requiredness=MetadataVisibility.SHOW),
    )

    sheet_name = "Requiredness_Demo"
    export_to_xlsx(products, demo_file, config=config, sheet_name=sheet_name)

    print("✓ Exported table with requiredness row")
    print("  Fields show:")
    print('  - "Required" for required fields (sku, name)')
    print('  - "Optional" for optional with trivial default (price)')
    print('  - "Optional (default: General)" for non-trivial default (category)')
    print('  - "Optional" for nullable fields (description)')


def demo_metadata_visibility_toggles(demo_file: Path):
    """Demonstrate metadata visibility toggle controls."""

    print("\n" + "=" * 50)
    print("9. Metadata Visibility Toggles")
    print("=" * 50)

    # Model with various metadata
    class SensorReading(BaseModel):
        sensor_id: str
        temperature: Annotated[
            float,
            XLSXMetadata(
                unit="°C",
                description="Temperature reading",
                meaning="sensor:temperature",
            ),
        ]
        humidity: Annotated[
            float,
            XLSXMetadata(
                unit="%",
                description="Relative humidity",
                meaning="sensor:humidity",
            ),
        ]

    readings = [
        SensorReading(sensor_id="S1", temperature=22.5, humidity=45.0),
    ]

    # Example 1: Hide units row
    config_hide_units = XLSXTableConfig(
        title="Readings - No Units Row",
        metadata_visibility=MetadataToggleConfig(unit=MetadataVisibility.HIDE),
    )
    export_to_xlsx(
        readings, demo_file, config=config_hide_units, sheet_name="Hide_Units"
    )
    print("✓ Exported with units row hidden (HIDE mode)")

    # Example 2: Show requiredness but hide descriptions
    config_mixed = XLSXTableConfig(
        title="Readings - Custom Visibility",
        metadata_visibility=MetadataToggleConfig(
            requiredness=MetadataVisibility.SHOW,
            description=MetadataVisibility.HIDE,
        ),
    )
    export_to_xlsx(
        readings, demo_file, config=config_mixed, sheet_name="Mixed_Visibility"
    )
    print("✓ Exported with requiredness shown, descriptions hidden")

    # Example 3: Force show all metadata (even if empty)
    config_show_all = XLSXTableConfig(
        title="Readings - All Metadata",
        metadata_visibility=MetadataToggleConfig(
            unit=MetadataVisibility.SHOW,
            requiredness=MetadataVisibility.SHOW,
            description=MetadataVisibility.SHOW,
            meaning=MetadataVisibility.SHOW,
        ),
    )
    export_to_xlsx(
        readings, demo_file, config=config_show_all, sheet_name="All_Metadata"
    )
    print("✓ Exported with all metadata rows shown (SHOW mode)")

    print("\nVisibility modes:")
    print("  - AUTO: Show row if any field has that metadata (default)")
    print("  - SHOW: Always show the row (empty cells for fields without metadata)")
    print("  - HIDE: Never show the row (even if fields have metadata)")


def main():
    """Run all table data demonstrations."""

    print("XLSX TABLE DATA REPRESENTATIONS AND SERIALIZATION DEMO")
    print("=" * 60)
    print("Focus: Data handling, converters, and serialization for table format")

    # Output file
    demo_file = Path("table_data_demo_joins.xlsx")

    # Remove existing file to avoid conflicts
    if demo_file.exists():
        demo_file.unlink()

    try:
        demo_basic_table_format(demo_file)
        demo_builtin_converters(demo_file)
        demo_custom_serializers(demo_file)
        demo_list_to_pipe_conversion(demo_file)
        demo_model_joins(demo_file)
        demo_multi_row_joins(demo_file)
        demo_auto_detection(demo_file)
        demo_requiredness_row(demo_file)
        demo_metadata_visibility_toggles(demo_file)

        print("\n✅ All demonstrations completed successfully!")
        print(f"Demo file: {demo_file.absolute()}")
        print("\nSheets created:")
        print("• Employees_Basic - Basic table format")
        print("• Tasks_Converters - Built-in converters demo")
        print("• Projects_Custom - Custom serializers demo")
        print("• Skills_Pipe - Manual list to pipe conversion")
        print("• Employees_Joined - Model joins for flattening nested data")
        print("• Employee_Skills_MultiRow - Multi-row joins (multiple rows per record)")
        print("• Auto_List - Auto-detection with list")
        print("• Auto_Tuple - Auto-detection with tuple")
        print("• Explicit_Table - Explicit table format")
        print("• Requiredness_Demo - Requiredness row display")
        print("• Hide_Units - Metadata visibility toggle (HIDE)")
        print("• Mixed_Visibility - Requiredness shown, descriptions hidden")
        print("• All_Metadata - All metadata rows shown (SHOW mode)")

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
