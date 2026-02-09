#!/bin/bash
# prepare_drift_comment.sh
#
# Generates the PR comment body for OpenAPI spec drift detection.
# This script is used by the drift detection workflow to create comments
# when local specs differ from the central aap-openapi-specs repository.
#
# Usage: prepare_drift_comment.sh <has_breaking> <diff_file> <central_branch> [breaking_file]
#
# Arguments:
#   has_breaking   - "true" or "false" indicating if breaking changes were detected
#   diff_file      - Path to the file containing the formatted diff output
#   central_branch - The aap-openapi-specs branch being compared against
#   breaking_file  - Path to the file containing breaking changes (required if has_breaking=true)
#
# Output: Writes the complete PR comment body to stdout

set -e

HAS_BREAKING="${1:-false}"
DIFF_FILE="${2:-}"
CENTRAL_BRANCH="${3:-devel}"
BREAKING_FILE="${4:-}"

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
echo "## 📊 OpenAPI Spec Drift Detected"
echo ""
echo "_Compares this PR's spec against the centralized spec repository._"
echo ""

if [ "$HAS_BREAKING" = "true" ]; then
    echo "> [!CAUTION]"
    echo "> Drift includes **breaking API changes** compared to the central specification."
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
    echo "> The local OpenAPI spec differs from the central repository."
    echo ""
fi

echo "### Comparison Details"
echo ""
echo "| Location | Path |"
echo "|----------|------|"
echo "| **Local** | \`galaxy_ng/app/static/galaxy.json\` |"
echo "| **Central** | \`aap-openapi-specs/galaxy.json\` (branch: \`${CENTRAL_BRANCH}\`) |"
echo ""
echo "### API Diff"
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
echo "#### If changes are intentional:"
echo "1. Update central spec in [aap-openapi-specs](https://github.com/ansible-automation-platform/aap-openapi-specs)"
echo "2. Create PR to the \`${CENTRAL_BRANCH}\` branch"
echo "3. Link the aap-openapi-specs PR in this PR description"
echo ""
echo "#### If changes are unintentional:"
echo "1. Revert local spec changes in \`galaxy_ng/app/static/galaxy.json\`"
echo "2. Or update code to match central spec expectations"
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
echo "ℹ️ **Note**: This check is informational only and will not block the merge."
echo ""
echo "See [Handbook: OpenAPI Spec Drift Detection](https://handbook.eng.ansible.com/docs/CICD/Services/openapi-specification-drift-detection/) for details."
