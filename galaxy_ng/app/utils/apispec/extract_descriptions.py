#!/usr/bin/env python
"""
Script to extract operationId -> description mappings from OpenAPI spec.

Usage:
    python extract_descriptions.py galaxy.json > descriptions.yaml

The output is a YAML file with operationId as keys and descriptions as values,
formatted for easy human editing.
"""
import json
import sys

import yaml


def extract_descriptions(spec: dict) -> dict[str, str]:
    """
    Extract operationId -> description mappings from OpenAPI spec.

    Returns a dict mapping operationId to description text.
    """
    descriptions: dict[str, str] = {}
    paths = spec.get("paths", {})

    for _path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        for method in ("get", "post", "put", "patch", "delete", "head", "options"):
            if method in path_item and isinstance(path_item[method], dict):
                operation = path_item[method]
                op_id = operation.get("operationId")
                if op_id:
                    # Prefer x-ai-description, fallback to description, default to empty
                    desc = operation.get("x-ai-description") or operation.get("description") or ""
                    descriptions[op_id] = desc

    return descriptions


def format_yaml_output(descriptions: dict[str, str]) -> str:
    """
    Format descriptions as YAML with folded block scalars.

    Uses folded style (>) for all descriptions to ensure consistent formatting.
    """

    # Create a custom dumper
    class DescriptionDumper(yaml.SafeDumper):
        """Custom YAML dumper that uses folded style for strings."""

        pass

    def literal_representer(
        dumper: DescriptionDumper,
        data: str,
    ) -> yaml.ScalarNode:
        """Represent string as folded block scalar, or empty string for missing."""
        if not data:
            return dumper.represent_scalar("tag:yaml.org,2002:str", "", style="")
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=">")

    DescriptionDumper.add_representer(str, literal_representer)

    # Sort by operationId for consistent output
    sorted_descriptions = dict(sorted(descriptions.items()))

    return yaml.dump(
        sorted_descriptions,
        Dumper=DescriptionDumper,
        default_flow_style=False,
        allow_unicode=True,
        width=100,
        sort_keys=False,
    )


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python extract_descriptions.py <input_file>", file=sys.stderr)
        print("Example: python extract_descriptions.py galaxy.json > descriptions.yaml", file=sys.stderr)
        sys.exit(1)

    input_file = sys.argv[1]

    # Read input file
    with open(input_file, encoding="utf-8") as f:
        spec = json.load(f)

    # Extract descriptions
    descriptions = extract_descriptions(spec)

    # Output as YAML
    print(format_yaml_output(descriptions))


if __name__ == "__main__":
    main()
