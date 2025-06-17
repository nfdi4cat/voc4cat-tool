#!/usr/bin/env python3
"""
Demo: Table Visual Formatting and Styling

This demo focuses on visual presentation, formatting, and styling for table format.
It demonstrates how to customize the appearance and layout of Excel tables.

Features demonstrated:
- Custom table titles and headers
- Field ordering and exclusion
- Field descriptions above headers
- Unit display in headers
- Custom display names
- Auto-filter and validation display
- Table styling and formatting
"""

from datetime import date
from enum import Enum
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel

from voc4cat.xlsx_api import export_to_xlsx
from voc4cat.xlsx_common import XLSXMetadata
from voc4cat.xlsx_table import XLSXTableConfig


# Enums
class Department(Enum):
    ENGINEERING = "engineering"
    MARKETING = "marketing"
    SALES = "sales"
    HR = "human_resources"
    FINANCE = "finance"


class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Model for styling demonstration
class Employee(BaseModel):
    """Employee model with various field types for styling demonstration."""

    employee_id: Annotated[
        int,
        XLSXMetadata(
            display_name="Employee ID",
            description="Unique employee identifier",
        ),
    ]

    first_name: Annotated[
        str,
        XLSXMetadata(
            display_name="First Name",
            description="Employee's first name",
        ),
    ]

    last_name: Annotated[
        str,
        XLSXMetadata(
            display_name="Last Name",
            description="Employee's last name",
        ),
    ]

    email: Annotated[
        str,
        XLSXMetadata(
            display_name="Email Address",
            description="Work email address",
        ),
    ]

    department: Annotated[
        Department,
        XLSXMetadata(
            display_name="Department",
            description="Employee's department",
        ),
    ]

    hire_date: Annotated[
        date,
        XLSXMetadata(
            display_name="Hire Date",
            description="Date when employee was hired",
        ),
    ]

    salary: Annotated[
        float,
        XLSXMetadata(
            display_name="Annual Salary",
            description="Annual salary amount",
            unit="USD",
        ),
    ]

    status: Annotated[
        Status,
        XLSXMetadata(
            display_name="Status",
            description="Current employment status",
        ),
    ] = Status.ACTIVE

    is_manager: Annotated[
        bool,
        XLSXMetadata(
            display_name="Manager?",
            description="Whether employee is a manager",
        ),
    ] = False

    performance_rating: Annotated[
        float | None,
        XLSXMetadata(
            display_name="Performance Rating",
            description="Latest performance rating",
            unit="scale 1-5",
        ),
    ] = None


# Model for units demonstration
class Product(BaseModel):
    """Product model with units for styling demonstration."""

    product_id: Annotated[
        str,
        XLSXMetadata(
            display_name="Product ID",
            description="Unique product identifier",
        ),
    ]

    name: Annotated[
        str,
        XLSXMetadata(
            display_name="Product Name",
            description="Product name",
        ),
    ]

    price: Annotated[
        float,
        XLSXMetadata(
            display_name="Price",
            description="Product price",
            unit="USD",
        ),
    ]

    weight: Annotated[
        float,
        XLSXMetadata(
            display_name="Weight",
            description="Product weight",
            unit="kg",
        ),
    ]

    length: Annotated[
        float,
        XLSXMetadata(
            display_name="Length",
            description="Product length",
            unit="cm",
        ),
    ]

    width: Annotated[
        float,
        XLSXMetadata(
            display_name="Width",
            description="Product width",
            unit="cm",
        ),
    ]

    height: Annotated[
        float,
        XLSXMetadata(
            display_name="Height",
            description="Product height",
            unit="cm",
        ),
    ]

    in_stock: Annotated[
        bool,
        XLSXMetadata(
            display_name="In Stock?",
            description="Whether product is in stock",
        ),
    ] = True


def create_sample_data():
    """Create sample data for styling demonstrations."""

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
            performance_rating=4.5,
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
            performance_rating=4.2,
        ),
        Employee(
            employee_id=3,
            first_name="Carol",
            last_name="Davis",
            email="carol.davis@company.com",
            department=Department.SALES,
            hire_date=date(2021, 8, 20),
            salary=70000.0,
            status=Status.ACTIVE,
            is_manager=False,
            performance_rating=4.8,
        ),
        Employee(
            employee_id=4,
            first_name="David",
            last_name="Wilson",
            email="david.wilson@company.com",
            department=Department.HR,
            hire_date=date(2020, 11, 5),
            salary=75000.0,
            status=Status.INACTIVE,
            is_manager=True,
            performance_rating=4.3,
        ),
    ]

    products = [
        Product(
            product_id="WIDGET-001",
            name="Premium Widget",
            price=29.99,
            weight=0.5,
            length=15.0,
            width=10.0,
            height=5.0,
            in_stock=True,
        ),
        Product(
            product_id="GADGET-002",
            name="Smart Gadget",
            price=149.99,
            weight=2.3,
            length=25.0,
            width=15.0,
            height=8.0,
            in_stock=False,
        ),
        Product(
            product_id="DEVICE-003",
            name="Ultra Device",
            price=599.99,
            weight=1.8,
            length=30.0,
            width=20.0,
            height=12.0,
            in_stock=True,
        ),
    ]

    return employees, products


def demo_basic_table_styling(demo_file: Path):
    """Demonstrate basic table styling options."""

    print("\\n" + "=" * 50)
    print("1. Basic Table Styling")
    print("=" * 50)

    employees, _ = create_sample_data()

    # Basic table with title
    config = XLSXTableConfig(
        title="Employee Directory",
        start_row=2,  # Leave space for title
        auto_filter=True,
    )

    export_to_xlsx(
        employees,
        demo_file,
        format_type="table",
        config=config,
        sheet_name="Basic_Styled_Table",
    )
    print("✓ Exported basic styled table to 'Basic_Styled_Table'")
    print("  - Table title: 'Employee Directory'")
    print("  - Auto-filter enabled")
    print("  - Validation always enabled")


def demo_field_ordering_and_exclusion(demo_file: Path):
    """Demonstrate custom field ordering and exclusion."""

    print("\\n" + "=" * 50)
    print("2. Field Ordering and Exclusion")
    print("=" * 50)

    employees, _ = create_sample_data()

    # Custom field order and exclusions
    config = XLSXTableConfig(
        title="Employee Summary (Custom Layout)",
        field_order=[
            "employee_id",
            "last_name",
            "first_name",
            "department",
            "status",
            "salary",
            "hire_date",
            "is_manager",
        ],
        exclude_fields={"performance_rating"},  # Exclude performance rating
        start_row=2,
        auto_filter=True,
    )

    export_to_xlsx(
        employees,
        demo_file,
        format_type="table",
        config=config,
        sheet_name="Custom_Field_Order",
    )
    print("✓ Exported table with custom field order to 'Custom_Field_Order'")
    print("  - Custom field order: ID, Last Name, First Name, Department, etc.")
    print("  - Excluded fields: performance_rating")


def demo_field_descriptions(demo_file: Path):
    """Demonstrate field descriptions above headers."""

    print("\\n" + "=" * 50)
    print("3. Field Descriptions Above Headers")
    print("=" * 50)

    employees, _ = create_sample_data()

    # Table with descriptions
    config = XLSXTableConfig(
        title="Employee Directory with Field Descriptions",
        start_row=3,  # More space for title and descriptions
        auto_filter=True,
    )

    export_to_xlsx(
        employees,
        demo_file,
        format_type="table",
        config=config,
        sheet_name="Table_With_Descriptions",
    )
    print("✓ Exported table with field descriptions to 'Table_With_Descriptions'")
    print("  - Field descriptions always appear above column headers")
    print("  - Helps users understand each column's purpose")


def demo_unit_display(demo_file: Path):
    """Demonstrate unit display in headers."""

    print("\\n" + "=" * 50)
    print("4. Unit Display in Headers")
    print("=" * 50)

    _, products = create_sample_data()

    # Table with units
    config = XLSXTableConfig(
        title="Product Catalog with Units",
        start_row=3,
        auto_filter=True,
    )

    export_to_xlsx(
        products,
        demo_file,
        format_type="table",
        config=config,
        sheet_name="Table_With_Units",
    )
    print("✓ Exported table with units to 'Table_With_Units'")
    print("  - Units always appear in column headers")
    print("  - Format: Price (USD), Weight (kg), Length (cm), etc.")


def demo_custom_display_names(demo_file: Path):
    """Demonstrate custom display names for professional headers."""

    print("\\n" + "=" * 50)
    print("5. Custom Display Names")
    print("=" * 50)

    employees, _ = create_sample_data()

    # Table with custom display names
    config = XLSXTableConfig(
        title="Employee Directory (Professional Headers)",
        start_row=2,
        auto_filter=True,
    )

    export_to_xlsx(
        employees,
        demo_file,
        format_type="table",
        config=config,
        sheet_name="Custom_Display_Names",
    )
    print("✓ Exported table with custom display names to 'Custom_Display_Names'")
    print("  - Headers use display_name instead of field_name")
    print("  - 'Employee ID' instead of 'employee_id'")
    print("  - 'Email Address' instead of 'email'")
    print("  - 'Manager?' instead of 'is_manager'")


def demo_comprehensive_styling(demo_file: Path):
    """Demonstrate comprehensive styling with all features."""

    print("\\n" + "=" * 50)
    print("6. Comprehensive Styling")
    print("=" * 50)

    employees, _ = create_sample_data()

    # Table with all styling features
    config = XLSXTableConfig(
        title="Complete Employee Directory (All Features)",
        start_row=4,  # Extra space for all headers
        field_order=[
            "employee_id",
            "last_name",
            "first_name",
            "email",
            "department",
            "hire_date",
            "salary",
            "performance_rating",
            "status",
            "is_manager",
        ],
        auto_filter=True,
    )

    export_to_xlsx(
        employees,
        demo_file,
        format_type="table",
        config=config,
        sheet_name="Comprehensive_Styling",
    )
    print("✓ Exported comprehensive styled table to 'Comprehensive_Styling'")
    print("  - Professional table title")
    print("  - Custom field ordering")
    print("  - Field descriptions always above headers")
    print("  - Unit display for salary and performance rating")
    print("  - Auto-filter enabled")
    print("  - Validation always enabled")


def demo_minimal_styling(demo_file: Path):
    """Demonstrate minimal styling for simple tables."""

    print("\\n" + "=" * 50)
    print("7. Minimal Styling")
    print("=" * 50)

    employees, _ = create_sample_data()

    # Minimal table - just the essentials
    config = XLSXTableConfig(
        title="Simple Employee List",
        include_fields={
            "employee_id",
            "first_name",
            "last_name",
            "department",
            "status",
        },
        start_row=2,
        auto_filter=False,
    )

    export_to_xlsx(
        employees,
        demo_file,
        format_type="table",
        config=config,
        sheet_name="Minimal_Styling",
    )
    print("✓ Exported minimal styled table to 'Minimal_Styling'")
    print("  - Only essential fields included")
    print("  - Descriptions and units always shown")
    print("  - Clean, simple layout")


def demo_comparison_tables(demo_file: Path):
    """Demonstrate different styling approaches for comparison."""

    print("\\n" + "=" * 50)
    print("8. Styling Comparison")
    print("=" * 50)

    employees, _ = create_sample_data()

    # Same data, different styling approaches

    # Approach 1: Developer-friendly (technical)
    dev_config = XLSXTableConfig(
        title="Employee Data (Technical View)",
        start_row=2,
        auto_filter=True,
    )

    export_to_xlsx(
        employees,
        demo_file,
        format_type="table",
        config=dev_config,
        sheet_name="Developer_Style",
    )
    print("✓ Exported developer-style table to 'Developer_Style'")

    # Approach 2: Executive-friendly (business)
    exec_config = XLSXTableConfig(
        title="Employee Summary (Executive View)",
        field_order=[
            "last_name",
            "first_name",
            "department",
            "salary",
            "performance_rating",
            "status",
            "is_manager",
        ],
        exclude_fields={"employee_id", "email", "hire_date"},
        start_row=2,
        auto_filter=True,
    )

    export_to_xlsx(
        employees,
        demo_file,
        format_type="table",
        config=exec_config,
        sheet_name="Executive_Style",
    )
    print("✓ Exported executive-style table to 'Executive_Style'")

    # Approach 3: HR-friendly (human resources)
    hr_config = XLSXTableConfig(
        title="Employee Records (HR View)",
        field_order=[
            "employee_id",
            "first_name",
            "last_name",
            "department",
            "hire_date",
            "status",
            "performance_rating",
        ],
        exclude_fields={"salary", "email"},  # Exclude sensitive information
        start_row=3,
        auto_filter=True,
    )

    export_to_xlsx(
        employees,
        demo_file,
        format_type="table",
        config=hr_config,
        sheet_name="HR_Style",
    )
    print("✓ Exported HR-style table to 'HR_Style'")

    print("  - Same data, different presentations")
    print("  - Technical view: All fields with descriptions and units")
    print("  - Executive view: Key metrics, minimal fields")
    print("  - HR view: Employee focus, no salary")


def main():
    """Run all table styling demonstrations."""

    print("XLSX TABLE VISUAL FORMATTING AND STYLING DEMO")
    print("=" * 60)
    print("Focus: Visual presentation, formatting, and styling for tables")

    # Output file
    demo_file = Path("table_styling_demo.xlsx")

    # Remove existing file to avoid conflicts
    if demo_file.exists():
        demo_file.unlink()

    try:
        demo_basic_table_styling(demo_file)
        demo_field_ordering_and_exclusion(demo_file)
        demo_field_descriptions(demo_file)
        demo_unit_display(demo_file)
        demo_custom_display_names(demo_file)
        demo_comprehensive_styling(demo_file)
        demo_minimal_styling(demo_file)
        demo_comparison_tables(demo_file)

        print("\\n✅ All demonstrations completed successfully!")
        print(f"Demo file: {demo_file.absolute()}")
        print("\\nSheets created:")
        print("• Basic_Styled_Table - Basic table with title and filters")
        print("• Custom_Field_Order - Custom field ordering and exclusions")
        print("• Table_With_Descriptions - Field descriptions always above headers")
        print("• Table_With_Units - Units always in headers")
        print("• Custom_Display_Names - Professional custom headers")
        print("• Comprehensive_Styling - All styling features combined")
        print("• Minimal_Styling - Clean, simple layout")
        print("• Developer_Style - Technical view with all details")
        print("• Executive_Style - Business view with key metrics")
        print("• HR_Style - Human resources view")

    except Exception as e:
        print(f"\\n❌ Demo failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
