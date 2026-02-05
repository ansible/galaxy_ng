#!/bin/bash
#
# Compare OpenAPI specifications and generate formatted diff output
#
# Usage:
#   compare_openapi_specs.sh [--simple|--structured] <base_spec> <source_spec> <output_file>
#
# Modes:
#   --structured  Use oasdiff for structured, detailed API comparison (default)
#   --simple      Use basic diff for quick file comparison
#
# Arguments:
#   base_spec    - Path to the base/original OpenAPI spec file
#   source_spec  - Path to the source/modified OpenAPI spec file
#   output_file  - Path where the formatted diff output will be written
#
# Exit codes:
#   0 - No changes detected
#   1 - Changes detected (output written to file)
#   2 - Error (missing arguments or files)
#
# GitHub Actions Output:
#   Sets GITHUB_OUTPUT variable 'has_changes' to true/false if GITHUB_OUTPUT is set
#   Sets GITHUB_OUTPUT variable 'drift_detected' to true/false if GITHUB_OUTPUT is set

set -euo pipefail

# Colors for terminal output (disabled in CI)
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

# Function to print usage
usage() {
    cat << EOF
Usage: $(basename "$0") [--simple|--structured] <base_spec> <source_spec> <output_file>

Compare two OpenAPI specification files and generate a formatted diff.

Modes:
    --structured    Use oasdiff for structured, detailed API comparison (default)
                    Detects endpoint changes, breaking changes, schema modifications
                    Requires: oasdiff installed

    --simple        Use basic diff for quick file comparison
                    Faster, no dependencies, good for drift detection
                    Requires: diff (built-in)

Arguments:
    base_spec       Path to the base/original OpenAPI spec file
    source_spec     Path to the source/modified OpenAPI spec file
    output_file     Path where the formatted diff output will be written

Examples:
    # Structured comparison (PR review)
    $(basename "$0") --structured base/galaxy.json source/galaxy.json /tmp/diff.md

    # Simple comparison (drift detection)
    $(basename "$0") --simple local/galaxy.json central/galaxy.json /tmp/diff.md

    # Default mode (structured)
    $(basename "$0") base/galaxy.json source/galaxy.json /tmp/diff.md

Exit codes:
    0 - No changes detected
    1 - Changes detected (output written to file)
    2 - Error (missing arguments or files)
EOF
}

# Function to log messages
log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

# Parse mode flag
MODE="structured"  # Default mode
if [ $# -ge 1 ] && [[ "$1" == --* ]]; then
    case "$1" in
        --simple)
            MODE="simple"
            shift
            ;;
        --structured)
            MODE="structured"
            shift
            ;;
        *)
            log_error "Unknown flag: $1"
            usage
            exit 2
            ;;
    esac
fi

# Validate arguments
if [ $# -ne 3 ]; then
    log_error "Invalid number of arguments"
    usage
    exit 2
fi

BASE_SPEC="$1"
SOURCE_SPEC="$2"
OUTPUT_FILE="$3"

# Validate input files exist
if [ ! -f "$BASE_SPEC" ]; then
    log_error "Base spec file not found: $BASE_SPEC"
    exit 2
fi

if [ ! -f "$SOURCE_SPEC" ]; then
    log_error "Source spec file not found: $SOURCE_SPEC"
    exit 2
fi

# Ensure output directory exists
OUTPUT_DIR=$(dirname "$OUTPUT_FILE")
mkdir -p "$OUTPUT_DIR"

log_info "Comparing OpenAPI specifications ($MODE mode):"
log_info "  Base:   $BASE_SPEC"
log_info "  Source: $SOURCE_SPEC"
log_info "  Output: $OUTPUT_FILE"

# Perform comparison based on mode
if [ "$MODE" = "structured" ]; then
    #
    # STRUCTURED MODE: Use oasdiff for detailed API comparison
    #

    # Check if oasdiff is available
    if ! command -v oasdiff &> /dev/null; then
        log_error "oasdiff is not installed or not in PATH"
        log_error "Install it from: https://github.com/oasdiff/oasdiff"
        log_error "Or use --simple mode for basic diff comparison"
        exit 2
    fi

    # Generate the full diff in markdown format
    DIFF_OUTPUT=$(oasdiff diff \
        "$BASE_SPEC" \
        "$SOURCE_SPEC" \
        --format markdown 2>&1) || true

    # Check if there are any changes
    if [ -z "$DIFF_OUTPUT" ] || [ "$DIFF_OUTPUT" = "No changes" ]; then
        log_info "No API schema changes detected"

        # Set GitHub Actions output if running in CI
        if [ -n "${GITHUB_OUTPUT:-}" ]; then
            echo "has_changes=false" >> "$GITHUB_OUTPUT"
            echo "drift_detected=false" >> "$GITHUB_OUTPUT"
        fi

        # Write empty result to output file
        echo "No changes detected" > "$OUTPUT_FILE"

        exit 0
    else
        log_warn "API schema changes detected"

        # Set GitHub Actions output if running in CI
        if [ -n "${GITHUB_OUTPUT:-}" ]; then
            echo "has_changes=true" >> "$GITHUB_OUTPUT"
            echo "drift_detected=true" >> "$GITHUB_OUTPUT"
        fi

        # Clean up the oasdiff output:
        # 1. Remove lines that are only dashes (separators)
        # 2. Wrap endpoint lines (METHOD /path) in backticks for better markdown formatting
        # 3. Add horizontal rules before Deleted and Modified sections for visual separation
        echo "$DIFF_OUTPUT" | \
            sed '/^-\+$/d' | \
            sed -E 's/^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS) (\/[^ ]*)/`\1 \2`/' | \
            sed 's/^### Deleted Endpoints/---\n### Deleted Endpoints/' | \
            sed 's/^### Modified Endpoints/---\n### Modified Endpoints/' \
            > "$OUTPUT_FILE"

        log_info "Diff output written to: $OUTPUT_FILE"

        exit 1
    fi

elif [ "$MODE" = "simple" ]; then
    #
    # SIMPLE MODE: Use basic diff for quick comparison
    #

    # Check if files are identical using diff -q (quiet mode)
    if diff -q "$BASE_SPEC" "$SOURCE_SPEC" > /dev/null 2>&1; then
        log_info "No differences detected - files are identical"

        # Set GitHub Actions output if running in CI
        if [ -n "${GITHUB_OUTPUT:-}" ]; then
            echo "has_changes=false" >> "$GITHUB_OUTPUT"
            echo "drift_detected=false" >> "$GITHUB_OUTPUT"
        fi

        # Write empty result to output file
        echo "No changes detected" > "$OUTPUT_FILE"

        exit 0
    else
        log_warn "Differences detected"

        # Set GitHub Actions output if running in CI
        if [ -n "${GITHUB_OUTPUT:-}" ]; then
            echo "has_changes=true" >> "$GITHUB_OUTPUT"
            echo "drift_detected=true" >> "$GITHUB_OUTPUT"
        fi

        # Generate unified diff with markdown code block
        {
            echo '```diff'
            diff -u "$BASE_SPEC" "$SOURCE_SPEC" || true
            echo '```'
        } > "$OUTPUT_FILE"

        log_info "Diff output written to: $OUTPUT_FILE"

        exit 1
    fi
else
    log_error "Unknown mode: $MODE"
    usage
    exit 2
fi
