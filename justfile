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
    uv run sphinx-build -b html docs/ docs/_build/

# Detect code duplicates using PMD CPD
[group('development')]
duplicates TOKENS="100" OUTPUT=".duplicates.txt" *DIRS:
    @echo "Running PMD CPD to detect duplicates..."
    @echo "  Minimum tokens (raw arg): {{TOKENS}}"
    @echo "  Output file: {{OUTPUT}}"
    @echo "  Directories (raw args): {{DIRS}}"
    @echo ""
    @-rm -f {{OUTPUT}} 2>/dev/null || true
    @TOKENS_RAW="{{TOKENS}}"; DIRS_RAW="{{DIRS}}"; DEFAULT_TOKENS="100"; if echo "$TOKENS_RAW" | grep -Eq '^[0-9]+$'; then MIN_TOKENS="$TOKENS_RAW"; DIRS_ALL="$DIRS_RAW"; else MIN_TOKENS="$DEFAULT_TOKENS"; DIRS_ALL="$TOKENS_RAW $DIRS_RAW"; fi; if [ -z "$(echo "$DIRS_ALL" | tr -d ' ')" ]; then DIRS_ALL="src/ tests/"; fi; DIR_FLAGS=""; for d in $DIRS_ALL; do DIR_FLAGS="$DIR_FLAGS --dir $d"; done; echo "  Minimum tokens (effective): $MIN_TOKENS"; echo "  Directories (effective): $DIRS_ALL"; if command -v pmd.bat >/dev/null 2>&1; then pmd.bat cpd --minimum-tokens "$MIN_TOKENS" --language python $DIR_FLAGS --format text --report-file {{OUTPUT}}; elif [ -f "C:/dev/pmd-bin-7.16.0/bin/pmd.bat" ]; then "C:/dev/pmd-bin-7.16.0/bin/pmd.bat" cpd --minimum-tokens "$MIN_TOKENS" --language python $DIR_FLAGS --format text --report-file {{OUTPUT}}; else pmd cpd --minimum-tokens "$MIN_TOKENS" --language python $DIR_FLAGS --format text --report-file {{OUTPUT}}; fi; EXIT_CODE=$?; if [ $EXIT_CODE -eq 0 ]; then echo "✓ No duplicates found (results in {{OUTPUT}})"; elif [ $EXIT_CODE -eq 4 ]; then echo "✓ Duplicates found and saved to {{OUTPUT}}"; else echo "✗ PMD failed with exit code $EXIT_CODE"; exit $EXIT_CODE; fi
