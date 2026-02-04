#!/usr/bin/env python
"""
Script to update OpenAPI spec tags from a YAML file.

Usage:
    python update_tags.py tags.yaml galaxy.json
    python update_tags.py tags.yaml galaxy.json --diff-only

The script reads tags from the YAML file and updates the JSON spec
with any changed tags. Only modified tags are updated.
"""
import argparse
import json
import sys
from typing import Any

import yaml


def load_tags(yaml_file: str) -> dict[str, list[str]]:
    """Load operationId -> tags mappings from YAML file."""
    with open(yaml_file, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_spec(json_file: str) -> dict[str, Any]:
    """Load OpenAPI spec from JSON file."""
    with open(json_file, encoding="utf-8") as f:
        return json.load(f)


def find_operation_by_id(
    spec: dict[str, Any],
    operation_id: str,
) -> tuple[str, str, dict[str, Any]] | None:
    """
    Find an operation in the spec by its operationId.

    Returns (path, method, operation_dict) or None if not found.
    """
    paths = spec.get("paths", {})
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        for method in ("get", "post", "put", "patch", "delete", "head", "options"):
            if method in path_item and isinstance(path_item[method], dict):
                operation = path_item[method]
                if operation.get("operationId") == operation_id:
                    return path, method, operation

    return None


def get_current_tags(operation: dict[str, Any]) -> list[str]:
    """Get current tags from operation."""
    return operation.get("tags", [])


def update_tags(
    spec: dict[str, Any],
    tags_map: dict[str, list[str]],
    diff_only: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    Update spec with tags from YAML.

    Returns:
        - Updated spec (or original if diff_only)
        - List of changes made (each with operationId, old, new)
    """
    changes: list[dict[str, Any]] = []

    for op_id, new_tags in tags_map.items():
        result = find_operation_by_id(spec, op_id)
        if result is None:
            print(f"Warning: operationId '{op_id}' not found in spec", file=sys.stderr)
            continue

        path, method, operation = result
        current_tags = get_current_tags(operation)

        # Compare sorted lists for equality
        if sorted(current_tags) != sorted(new_tags):
            changes.append({
                "operationId": op_id,
                "path": path,
                "method": method,
                "old": current_tags,
                "new": new_tags,
            })

            if not diff_only:
                # Update the tags
                operation["tags"] = new_tags

    return spec, changes


def print_diff(changes: list[dict[str, Any]]) -> None:
    """Print a summary of changes."""
    if not changes:
        print("No changes detected.")
        return

    print(f"\n{'='*60}")
    print(f"Changes: {len(changes)} tag(s) would be updated")
    print(f"{'='*60}\n")

    for change in changes:
        print(f"Operation: {change['operationId']}")
        print(f"  Path: {change['path']}")
        print(f"  Method: {change['method'].upper()}")
        print(f"  Old: {change['old']}")
        print(f"  New: {change['new']}")
        print()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Update OpenAPI spec tags from YAML file"
    )
    parser.add_argument(
        "yaml_file",
        help="Path to YAML file containing tags",
    )
    parser.add_argument(
        "json_file",
        help="Path to OpenAPI spec JSON file",
    )
    parser.add_argument(
        "--diff-only",
        action="store_true",
        help="Only show what would be changed, don't write to file",
    )

    args = parser.parse_args()

    # Load files
    try:
        tags_map = load_tags(args.yaml_file)
    except FileNotFoundError:
        print(f"Error: YAML file not found: {args.yaml_file}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        spec = load_spec(args.json_file)
    except FileNotFoundError:
        print(f"Error: JSON file not found: {args.json_file}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON file: {e}", file=sys.stderr)
        sys.exit(1)

    # Update tags
    updated_spec, changes = update_tags(
        spec,
        tags_map,
        diff_only=args.diff_only,
    )

    # Print summary
    print_diff(changes)

    if args.diff_only:
        print("(--diff-only mode: no changes written)")
    else:
        # Write updated spec back to file
        with open(args.json_file, "w", encoding="utf-8") as f:
            json.dump(updated_spec, f, indent=2)
        print(f"Updated {len(changes)} tag(s) in {args.json_file}")


if __name__ == "__main__":
    main()
