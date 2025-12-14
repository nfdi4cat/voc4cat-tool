# voc4cat-tool - Essential Development Commands

# Show available commands
default:
    @just --list

# Run all tests
[group('testing')]
test *ARGS:
    @echo "Running unit tests..."
    uv run python -m pytest tests/ -v {{ARGS}}

# Run all tests with coverage report
[group('testing')]
cov *ARGS:
    @echo "Running all tests with coverage..."
    uv run python -m coverage run -m pytest {{ARGS}}
    uv run python -m coverage combine
    uv run python -m coverage report
    uv run python -m coverage html

# Format and lint for code quality
[group('development')]
lint:
    @echo "Formatting code..."
    uv run ruff format src/ example/ tests/
    @echo "Checking code quality..."
    uv run ruff check --fix src/ example/ tests/
    # finally format fixed code
    uv run ruff format src/ example/ tests/

# Type check code with mypy and ty
[group('development')]
typecheck:
    @echo "Running mypy type checks..."
    uv run mypy src/
    @echo "Running ty type checks..."
    uv run ty check src/

# Build Sphinx documentation
[group('development')]
docs:
    @echo "Building Sphinx documentation..."
    uv run sphinx-build -M html docs/ docs/_build/

# Detect code duplicates using PMD CPD
[group('development')]
duplicates TOKENS="100" OUTPUT=".duplicates.txt" *DIRS:
    @echo "Running PMD CPD to detect duplicates..."
    @echo "  Minimum tokens: {{TOKENS}}"
    @echo "  Output file: {{OUTPUT}}"
    @echo "  Directories: {{if DIRS == "" { "src/ tests/ (default)" } else { DIRS } }}"
    @echo ""
    @-rm -f {{OUTPUT}} 2>/dev/null || true
    @if command -v pmd.bat >/dev/null 2>&1; then pmd.bat cpd --minimum-tokens {{TOKENS}} --language python {{if DIRS == "" { "--dir src/ --dir tests/" } else { replace_regex(DIRS, "([^ ]+)", "--dir $1") } }} --format text --report-file {{OUTPUT}}; elif [ -f "C:/dev/pmd-bin-7.16.0/bin/pmd.bat" ]; then "C:/dev/pmd-bin-7.16.0/bin/pmd.bat" cpd --minimum-tokens {{TOKENS}} --language python {{if DIRS == "" { "--dir src/ --dir tests/" } else { replace_regex(DIRS, "([^ ]+)", "--dir $1") } }} --format text --report-file {{OUTPUT}}; else pmd cpd --minimum-tokens {{TOKENS}} --language python {{if DIRS == "" { "--dir src/ --dir tests/" } else { replace_regex(DIRS, "([^ ]+)", "--dir $1") } }} --format text --report-file {{OUTPUT}}; fi; EXIT_CODE=$?; if [ $EXIT_CODE -eq 0 ]; then echo "✓ No duplicates found (results in {{OUTPUT}})"; elif [ $EXIT_CODE -eq 4 ]; then echo "✓ Duplicates found and saved to {{OUTPUT}}"; else echo "✗ PMD failed with exit code $EXIT_CODE"; exit $EXIT_CODE; fi
