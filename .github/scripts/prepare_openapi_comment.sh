#!/bin/bash
# prepare_openapi_comment.sh
#
# Generates a unified PR comment covering both intra-repo schema changes
# and central-repo drift detection.
#
# Usage:
#   prepare_openapi_comment.sh \
#     <pr_has_changes> <pr_has_breaking> <pr_diff_file> <pr_breaking_file> \
#     <drift_detected> <drift_has_breaking> <drift_diff_file> <drift_breaking_file> \
#     <central_branch>
#
# All arguments are positional. Pass empty string or "false" to skip a section.

set -e

PR_HAS_CHANGES="${1:-false}"
PR_HAS_BREAKING="${2:-false}"
PR_DIFF_FILE="${3:-}"
PR_BREAKING_FILE="${4:-}"
DRIFT_DETECTED="${5:-false}"
DRIFT_HAS_BREAKING="${6:-false}"
DRIFT_DIFF_FILE="${7:-}"
DRIFT_BREAKING_FILE="${8:-}"
CENTRAL_BRANCH="${9:-devel}"

echo "## OpenAPI Spec Review"
echo ""

# ── Section 1: PR schema changes ──────────────────────────────────────
if [ "$PR_HAS_CHANGES" = "true" ]; then
    echo "### Schema Changes in This PR"
    echo ""
    echo "_Comparing this PR against the target branch._"
    echo ""

    if [ "$PR_HAS_BREAKING" = "true" ] && [ -f "$PR_BREAKING_FILE" ]; then
        echo "> [!CAUTION]"
        echo "> This PR introduces **breaking changes** to the OpenAPI schema."
        echo ""
        echo "<details>"
        echo "<summary>Breaking Changes</summary>"
        echo ""
        cat "$PR_BREAKING_FILE"
        echo ""
        echo "</details>"
        echo ""
    fi

    if [ -f "$PR_DIFF_FILE" ]; then
        echo "<details>"
        echo "<summary>View Full Diff</summary>"
        echo ""
        cat "$PR_DIFF_FILE"
        echo ""
        echo "</details>"
        echo ""
    fi
fi

# ── Section 2: Central repo drift ─────────────────────────────────────
if [ "$DRIFT_DETECTED" = "true" ]; then
    echo "### Drift from Central Spec"
    echo ""
    echo "_Comparing against \`aap-openapi-specs\` (branch: \`${CENTRAL_BRANCH}\`)._"
    echo ""

    if [ "$DRIFT_HAS_BREAKING" = "true" ] && [ -f "$DRIFT_BREAKING_FILE" ]; then
        echo "> [!CAUTION]"
        echo "> Drift includes **breaking API changes** compared to the central specification."
        echo ""
        echo "<details>"
        echo "<summary>Breaking Changes</summary>"
        echo ""
        cat "$DRIFT_BREAKING_FILE"
        echo ""
        echo "</details>"
        echo ""
    else
        echo "> [!WARNING]"
        echo "> The local spec differs from the central repository."
        echo ""
    fi

    echo "| Location | Path |"
    echo "|----------|------|"
    echo "| **Local** | \`galaxy_ng/app/static/galaxy.json\` |"
    echo "| **Central** | \`aap-openapi-specs/galaxy.json\` (branch: \`${CENTRAL_BRANCH}\`) |"
    echo ""

    if [ -f "$DRIFT_DIFF_FILE" ]; then
        echo "<details>"
        echo "<summary>View Drift Diff</summary>"
        echo ""
        cat "$DRIFT_DIFF_FILE"
        echo ""
        echo "</details>"
        echo ""
    fi
fi

# ── Footer ─────────────────────────────────────────────────────────────
echo "---"
echo ""
echo "### Action Required"
echo ""
echo "**If changes are intentional**, notify affected teams:"
echo "- [#forum-aap-testing-framework](https://redhat.enterprise.slack.com/archives/C04PF3DL9FF) - ATF client generation"
echo "- [#aap-ui](https://redhat.enterprise.slack.com/archives/C01HQHP1GFW) - UI API contracts"
echo "- [#wg-ansible-content-integration](https://redhat.enterprise.slack.com/archives/C07S39P2MJC) - Content integration"
echo ""
echo "**If unintended**, adjust your changes so the API contracts are preserved."
echo ""
echo "This check is informational and will not block the merge."
