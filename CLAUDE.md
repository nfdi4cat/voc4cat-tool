# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

voc4cat-tool is a command-line tool for collaborative management of SKOS vocabularies using Excel as a user-friendly interface. It's part of the NFDI4Cat ecosystem for catalysis-related sciences, designed to convert between Excel/XLSX and RDF/Turtle formats while providing validation and documentation generation.

## Development Commands

### Installation & Setup
```bash
# Install with development dependencies
uv pip install .[dev]

# Install with AI similarity checking features
pip install .[assistant]
```

### Testing
```bash
# Run all tests
pytest

# Run tests with coverage
coverage run -p -m pytest

# Generate coverage report
coverage report
```

### Linting & Code Quality
```bash
# Run linting with ruff
ruff check

# Auto-fix linting issues
ruff check --fix
```

### Building
```bash
# Build source and wheel distributions
hatch build
```

## Architecture

### Core CLI Commands
The tool provides three main CLI entry points:
- `voc4cat` - Main command with subcommands: transform, convert, check, docs
- `voc4cat-merge` - Vocabulary merging functionality
- `voc-assistant` - AI-powered similarity checking and consistency validation

### Key Modules
- **cli.py** - Main CLI interface with Click-based subcommands
- **convert.py** - Excel ↔ RDF conversion (primary functionality)
- **transform.py** - In-format transformations (indentation, ID generation)
- **check.py** - SHACL validation using vocpub profile + custom checks
- **docs.py** - HTML documentation generation using pyLODE
- **models.py** - Pydantic v2 data models for Excel validation
- **config.py** - TOML configuration file handling (idranges.toml)
- **assistant.py** - AI-powered similarity checking with sentence-transformers

### Configuration System
Projects use `idranges.toml` files to configure:
- ID ranges for different contributors (with ORCID/ROR identifiers)
- Vocabulary metadata and permanent IRI parts
- Multiple vocabularies per repository support

### Template System
Excel templates are stored in `src/voc4cat/templates/` and define the structure for vocabulary spreadsheets. The conversion system supports custom templates.

## Testing Strategy

- **96% minimum coverage requirement** - enforced in CI
- **pytest** framework with comprehensive test data in `tests/data/`
- **Template versioning** - `tests/templ_versions/` contains reference outputs for different Excel template versions
- **Parallel execution** - tests run with coverage combination for CI efficiency
- **Python 3.10-3.13 matrix testing** in CI

## CI/CD Pipeline

### GitHub Actions
- **ci.yml** - Tests across Python versions, generates coverage reports
- **pypi-publish.yml** - Automated publishing to TestPyPI (tags) and PyPI (releases)
- **Trusted publishing** - No API keys needed, uses GitHub OIDC

### Key CI Features
- Matrix testing across Python 3.10-3.13
- Coverage artifacts and HTML reports uploaded
- Dependabot for dependency updates
- Security-focused with pinned action versions

## Code Patterns

### Pydantic Models
The project uses Pydantic v2 for data validation. Models are defined in `models.py` and validate Excel data structures before RDF conversion.

### Error Handling
- Custom exceptions for different error types
- Validation errors collected and reported together
- CI-specific error formatting with `--ci-pre` and `--ci-post` flags

### SHACL Integration
Uses the vocpub SHACL profile for formal RDF validation. Custom SHACL shapes can be added to the profiles system.

## Development Notes

- **Hatchling build system** with VCS-based versioning
- **ruff** for linting with extensive rule selection
- **mypy** for type checking
- **Platform independent** - Windows, Linux, macOS support
- **Production-ready** - Version 1.0+ with comprehensive documentation

## Common Development Workflows

### Adding New Validation Rules
1. Add custom checks to `checks.py`
2. Integrate with `check.py` main validation flow
3. Add corresponding tests in `test_checks.py`

### Extending Excel Template Support
1. Add new template to `src/voc4cat/templates/`
2. Update conversion logic in `convert.py` if needed
3. Add test cases with expected outputs to `tests/templ_versions/`

### Adding New CLI Commands
1. Extend CLI in `cli.py` using Click decorators
2. Implement core functionality in appropriate module
3. Add comprehensive tests covering all options
