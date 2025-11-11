#!/usr/bin/env bash
# Local multi-version CI: Build and test researcharr across multiple Python versions
# Usage: ./scripts/ci-multi-version.sh [--skip-build] [--versions "3.10 3.11 3.12 3.13 3.14"]

set -euo pipefail

# Configuration
DEFAULT_VERSIONS="3.10 3.11 3.12 3.13 3.14"
SKIP_BUILD=false
VERSIONS="${DEFAULT_VERSIONS}"
TEST_FILE="tests/run/test_run.py"
IMAGE_PREFIX="researcharr:py"
IMAGE_SUFFIX="-debug"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --versions)
            VERSIONS="$2"
            shift 2
            ;;
        --help|-h)
            cat <<EOF
Local multi-version CI for researcharr

Usage: $0 [OPTIONS]

Options:
    --skip-build           Skip building Docker images, only run tests
    --versions "X.Y ..."   Space-separated Python versions to test (default: ${DEFAULT_VERSIONS})
    --help, -h             Show this help message

Examples:
    # Build and test all versions
    $0

    # Test only, using existing images
    $0 --skip-build

    # Test specific versions
    $0 --versions "3.11 3.12"

    # Build and test specific versions
    $0 --versions "3.10 3.13"
EOF
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}" >&2
            echo "Use --help for usage information" >&2
            exit 1
            ;;
    esac
done

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}researcharr Multi-Version CI Runner${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""
echo "Testing Python versions: ${VERSIONS}"
echo "Skip build: ${SKIP_BUILD}"
echo ""

# Track results
declare -A BUILD_RESULTS
declare -A TEST_RESULTS
FAILED_VERSIONS=()

# Build images
if [[ "${SKIP_BUILD}" == "false" ]]; then
    echo -e "${BLUE}[BUILD PHASE]${NC}"
    echo ""
    
    for version in ${VERSIONS}; do
        version_short=$(echo "${version}" | tr -d '.')
        image_name="${IMAGE_PREFIX}${version_short}${IMAGE_SUFFIX}"
        
        # Check if image already exists
        if docker image inspect "${image_name}" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Image exists: ${image_name} (skipping build)${NC}"
            BUILD_RESULTS["${version}"]="exists"
            echo ""
            continue
        fi
        
        echo -e "${YELLOW}Building ${image_name}...${NC}"
        if docker build \
            --target debug \
            --build-arg PY_VERSION="${version}" \
            -t "${image_name}" \
            . > "/tmp/researcharr-build-${version_short}.log" 2>&1; then
            echo -e "${GREEN}✓ Build succeeded: ${image_name}${NC}"
            BUILD_RESULTS["${version}"]="success"
        else
            echo -e "${RED}✗ Build failed: ${image_name}${NC}"
            echo "  Check /tmp/researcharr-build-${version_short}.log for details"
            BUILD_RESULTS["${version}"]="failed"
            FAILED_VERSIONS+=("${version}")
        fi
        echo ""
    done
else
    echo -e "${YELLOW}Skipping build phase (--skip-build)${NC}"
    echo ""
fi

# Run tests
echo -e "${BLUE}[TEST PHASE]${NC}"
echo ""

for version in ${VERSIONS}; do
    version_short=$(echo "${version}" | tr -d '.')
    image_name="${IMAGE_PREFIX}${version_short}${IMAGE_SUFFIX}"
    
    # Skip if build failed
    if [[ "${BUILD_RESULTS[${version}]:-}" == "failed" ]]; then
        echo -e "${YELLOW}⊘ Skipping tests for ${version} (build failed)${NC}"
        TEST_RESULTS["${version}"]="skipped"
        continue
    fi
    
    echo -e "${YELLOW}Testing ${image_name}...${NC}"
    
    # Check if image exists
    if ! docker image inspect "${image_name}" > /dev/null 2>&1; then
        echo -e "${RED}✗ Image not found: ${image_name}${NC}"
        echo "  Run without --skip-build to build images first"
        TEST_RESULTS["${version}"]="no-image"
        FAILED_VERSIONS+=("${version}")
        echo ""
        continue
    fi
    
    # Run pytest in container
    if docker run \
        --rm -t \
        --entrypoint pytest \
        -w /app \
        "${image_name}" \
        -q "${TEST_FILE}" \
        --maxfail=1 \
        --disable-warnings \
        2>&1 | tee "/tmp/researcharr-test-${version_short}.log" | grep -E "passed|failed|ERROR"; then
        echo -e "${GREEN}✓ Tests passed: Python ${version}${NC}"
        TEST_RESULTS["${version}"]="success"
    else
        echo -e "${RED}✗ Tests failed: Python ${version}${NC}"
        echo "  Check /tmp/researcharr-test-${version_short}.log for details"
        TEST_RESULTS["${version}"]="failed"
        FAILED_VERSIONS+=("${version}")
    fi
    echo ""
done

# Summary
echo ""
echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}SUMMARY${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""

echo "Build Results:"
for version in ${VERSIONS}; do
    result="${BUILD_RESULTS[${version}]:-skipped}"
    case "${result}" in
        success)
            echo -e "  Python ${version}: ${GREEN}✓ Built${NC}"
            ;;
        exists)
            echo -e "  Python ${version}: ${GREEN}✓ Exists${NC}"
            ;;
        failed)
            echo -e "  Python ${version}: ${RED}✗ Failed${NC}"
            ;;
        skipped)
            echo -e "  Python ${version}: ${YELLOW}⊘ Skipped${NC}"
            ;;
    esac
done

echo ""
echo "Test Results:"
for version in ${VERSIONS}; do
    result="${TEST_RESULTS[${version}]:-unknown}"
    case "${result}" in
        success)
            echo -e "  Python ${version}: ${GREEN}✓ Passed${NC}"
            ;;
        failed)
            echo -e "  Python ${version}: ${RED}✗ Failed${NC}"
            ;;
        skipped)
            echo -e "  Python ${version}: ${YELLOW}⊘ Skipped${NC}"
            ;;
        no-image)
            echo -e "  Python ${version}: ${RED}✗ No image${NC}"
            ;;
        *)
            echo -e "  Python ${version}: ${YELLOW}? Unknown${NC}"
            ;;
    esac
done

echo ""

# Exit with error if any version failed
if [[ ${#FAILED_VERSIONS[@]} -gt 0 ]]; then
    echo -e "${RED}Failed versions: ${FAILED_VERSIONS[*]}${NC}"
    echo ""
    exit 1
else
    echo -e "${GREEN}All versions passed!${NC}"
    echo ""
    exit 0
fi
