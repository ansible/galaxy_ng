#!/bin/bash
# prepare_schema_change_comment.sh
#
# Generates the PR comment body for OpenAPI schema change detection.
# This script is used by the OpenAPI schema change detection workflow and can be
# adapted for future drift detection workflows.
#
# Usage: prepare_schema_change_comment.sh <has_breaking> <diff_file> [breaking_file]
#
# Arguments:
#   has_breaking  - "true" or "false" indicating if breaking changes were detected
#   diff_file     - Path to the file containing the formatted diff output
#   breaking_file - Path to the file containing breaking changes (required if has_breaking=true)
#
# Output: Writes the complete PR comment body to stdout

set -e

HAS_BREAKING="${1:-false}"
DIFF_FILE="${2:-}"
BREAKING_FILE="${3:-}"

if [ -z "$DIFF_FILE" ]; then
    echo "Error: diff_file argument is required" >&2
    exit 1
fi

if [ ! -f "$DIFF_FILE" ]; then
    echo "Error: diff file not found: $DIFF_FILE" >&2
    exit 1
fi

if [ "$HAS_BREAKING" = "true" ] && [ ! -f "$BREAKING_FILE" ]; then
    echo "Error: breaking_file is required when has_breaking=true" >&2
    exit 1
fi

# Generate the comment body
echo "## 🔀 OpenAPI Schema Changes Detected"
echo ""
echo "_Compares this PR's spec against the target branch to detect API changes._"
echo ""

if [ "$HAS_BREAKING" = "true" ]; then
    echo "> [!CAUTION]"
    echo "> This PR introduces **breaking changes** to the OpenAPI schema."
    echo ""
    echo "### Breaking Changes"
    echo ""
    echo "<details>"
    echo "<summary>View Breaking Changes</summary>"
    echo ""
    cat "$BREAKING_FILE"
    echo ""
    echo "</details>"
    echo ""
else
    echo "> [!WARNING]"
    echo "> This PR modifies the OpenAPI schema. Please review the changes below."
    echo ""
fi

echo "### API Schema Changes"
echo ""
echo "These changes need to be synced to the centralized spec repository."
echo ""
echo "<details>"
echo "<summary>View Full Diff</summary>"
echo ""
cat "$DIFF_FILE"
echo ""
echo "</details>"
echo ""
echo "---"
echo ""
echo "### ✅ Action Required"
echo ""
echo "**If unintended**, adjust your changes so the API contracts are preserved."
echo ""
echo "**If intended**, please notify affected teams."
echo ""
echo "### 📢 Cross-Team Notifications"
echo ""
echo "Spec changes may impact:"
echo "- [#forum-aap-testing-framework](https://redhat.enterprise.slack.com/archives/C04PF3DL9FF) - ATF client generation"
echo "- [#aap-ui](https://redhat.enterprise.slack.com/archives/C01HQHP1GFW) - UI API contracts"
echo "- [#wg-ansible-content-integration](https://redhat.enterprise.slack.com/archives/C07S39P2MJC) - Content integration"
echo ""
echo "---"
echo ""
echo "ℹ️ **Note**: This check helps ensure API contract awareness across teams."
