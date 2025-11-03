#!/bin/bash
# Multi-version Python testing script for pre-commit
# Tests against available Python versions quickly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Running multi-version Python compatibility checks...${NC}"

# Available Python versions to test (only test what's available)
PYTHON_VERSIONS=("python3.9" "python3.10" "python3.11" "python3.12" "python3.13" "python3" "python")
TESTED_VERSIONS=()
FAILED_VERSIONS=()

# Track tested interpreters to avoid duplicates
TESTED_INTERPRETERS=()

# Quick syntax and import test for each available Python version
for py_cmd in "${PYTHON_VERSIONS[@]}"; do
    if command -v "$py_cmd" &> /dev/null; then
        # Get the actual Python version to avoid testing the same interpreter twice
        py_version=$($py_cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "unknown")

        # Skip if we've already tested this version
        if [[ " ${TESTED_INTERPRETERS[*]} " =~ $py_version ]]; then
            echo -e "  ${YELLOW}⚠ $py_cmd (Python $py_version) already tested${NC}"
            continue
        fi

        echo -e "Testing with ${YELLOW}$py_cmd${NC} (Python $py_version)..."
        TESTED_INTERPRETERS+=("$py_version")

        # Test basic import and syntax
        if $py_cmd -c "
import sys
print(f'✓ Python {sys.version_info.major}.{sys.version_info.minor} - Basic syntax OK')

# Test basic imports
try:
    import researcharr
    print('✓ researcharr import successful')
except Exception as e:
    print(f'✗ Import failed: {e}')
    sys.exit(1)
        " 2>/dev/null; then
            echo -e "  ${GREEN}✓ $py_cmd passed${NC}"
            TESTED_VERSIONS+=("$py_cmd")
        else
            echo -e "  ${RED}✗ $py_cmd failed${NC}"
            FAILED_VERSIONS+=("$py_cmd")
        fi
    else
        echo -e "  ${YELLOW}⚠ $py_cmd not available${NC}"
    fi
done

# Summary
echo
echo -e "${YELLOW}Multi-version test summary:${NC}"
echo -e "  Tested: ${#TESTED_VERSIONS[@]} versions"
echo -e "  Passed: ${GREEN}${TESTED_VERSIONS[*]}${NC}"

if [ ${#FAILED_VERSIONS[@]} -gt 0 ]; then
    echo -e "  Failed: ${RED}${FAILED_VERSIONS[*]}${NC}"
    echo -e "${RED}Some Python versions failed compatibility checks!${NC}"
    exit 1
else
    echo -e "${GREEN}All available Python versions passed!${NC}"
fi
