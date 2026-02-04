#!/usr/bin/env python
"""
Script to shorten and normalize OpenAPI operation IDs.

Usage:
    python id_fix.py [inputfile]
    python id_fix.py galaxy.json > galaxy_fixed.json

The script transforms operation IDs to be shorter while maintaining uniqueness.
MCP tool names should ideally be ~40 characters with a hard limit of 64.
"""
import asyncio
import json
import re
import sys
from typing import Any


# Words to remove from operation IDs (not meaningful for identification)
NOISE_WORDS = {
    "api",
    "galaxy",
    "plugin",
    "pulp_ansible",
    "default",
}

# Template parameter patterns to remove
TEMPLATE_PATTERN = re.compile(r"\{[^}]+\}")

# Pattern to extract parameter names from path
PARAM_EXTRACT_PATTERN = re.compile(r"\{([^}]+)\}")


def extract_operations(spec: dict[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
    """
    Extract all operations from the OpenAPI spec.

    Returns a dict: {path: {method: {operationId, deprecated}}}
    """
    operations: dict[str, dict[str, dict[str, Any]]] = {}
    paths = spec.get("paths", {})

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        operations[path] = {}
        for method in ("get", "post", "put", "patch", "delete", "head", "options"):
            if method in path_item and isinstance(path_item[method], dict):
                operation = path_item[method]
                if "operationId" in operation:
                    operations[path][method] = {
                        "operationId": operation["operationId"],
                        "deprecated": operation.get("deprecated", False),
                    }

    return operations


def normalize_path_segment(segment: str) -> str:
    """Normalize a path segment for use in operation ID."""
    # Remove template parameters
    segment = TEMPLATE_PATTERN.sub("", segment)
    # Replace hyphens with underscores
    segment = segment.replace("-", "_")
    # Remove leading/trailing underscores
    segment = segment.strip("_")
    return segment


def deduplicate_words(words: list[str]) -> list[str]:
    """Remove consecutive duplicate words."""
    if not words:
        return words

    result = [words[0]]
    for word in words[1:]:
        if word != result[-1]:
            result.append(word)
    return result


def extract_version(path: str) -> str | None:
    """Extract version from path (v1, v2, v3, etc.)."""
    match = re.search(r"/(v\d+)/", path)
    return match.group(1) if match else None


def has_ui_segment(path: str) -> bool:
    """Check if path contains UI segment."""
    return "/_ui/" in path or "_ui_" in path or "/_ui_" in path


def has_pulp_segment(path: str) -> bool:
    """Check if path contains pulp segment."""
    return "/pulp/" in path or path.startswith("pulp/")


def extract_feature_area(path: str) -> list[str]:
    """
    Extract meaningful path segments after version/ui/plugin markers.

    Returns the trailing portion of the path that identifies the resource.
    """
    # Split path and normalize segments
    segments = [s for s in path.split("/") if s]
    normalized = [normalize_path_segment(s) for s in segments]
    normalized = [s for s in normalized if s]

    # Find the start index after version or key markers
    start_idx = 0

    for i, seg in enumerate(segments):
        # Skip past version markers
        if re.match(r"v\d+$", seg):
            start_idx = i + 1
        # Skip past plugin marker
        elif seg == "plugin":
            start_idx = i + 1
        # Skip past _ui segment
        elif seg == "_ui":
            start_idx = i + 1

    # Get segments from start_idx
    feature_segments = normalized[start_idx:]

    # Filter out noise words
    feature_segments = [s for s in feature_segments if s.lower() not in NOISE_WORDS]

    # If nothing left after filtering, use a meaningful fallback
    # This handles root endpoints like /api/galaxy/, /api/galaxy/api/
    if not feature_segments:
        # Try to find the last meaningful segment before version/plugin/ui
        for i in range(start_idx - 1, -1, -1):
            seg = normalized[i] if i < len(normalized) else ""
            if seg and seg.lower() not in NOISE_WORDS:
                feature_segments = [seg]
                break

        # If still empty, use "root" to indicate a root endpoint
        if not feature_segments:
            feature_segments = ["root"]

    return feature_segments


def get_action_from_path(path: str) -> str | None:
    """
    Extract action from the path's last segment if it's a known action.

    For example: /sync/, /sign/, /download/ etc.
    """
    # Known actions that appear as path segments
    path_actions = {
        "sync",
        "sign",
        "download",
        "upload",
        "rebuild",
        "curate",
        "index",
        "avatar",
    }

    segments = [s for s in path.rstrip("/").split("/") if s]
    if segments:
        last_seg = segments[-1].lower().replace("-", "_")
        # Remove template parameters
        last_seg = TEMPLATE_PATTERN.sub("", last_seg).strip("_")
        if last_seg in path_actions:
            return last_seg

    return None


def path_ends_with_id(path: str) -> bool:
    """Check if path ends with an ID parameter like {id}, {pulp_id}, etc."""
    segments = [s for s in path.rstrip("/").split("/") if s]
    if segments:
        last_seg = segments[-1]
        return bool(TEMPLATE_PATTERN.fullmatch(last_seg))
    return False


def extract_path_parameters(path: str) -> list[str]:
    """
    Extract all parameter names from a path.

    Example: "/api/{distro_base_path}/{namespace}/{name}/" -> ["distro_base_path", "namespace", "name"]
    """
    return PARAM_EXTRACT_PATTERN.findall(path)


def get_last_path_fragment(path: str) -> str:
    """
    Get the last non-parameter segment from a path for disambiguation.

    Example: "/api/galaxy/api/" -> "api"
    Example: "/api/galaxy/content/{pk}/" -> "content"

    Note: Does not filter noise words since this is used for disambiguation
    where even "api" or "galaxy" can be meaningful differentiators.
    """
    segments = [s for s in path.rstrip("/").split("/") if s]
    # Walk backwards to find first non-parameter segment
    for seg in reversed(segments):
        if not TEMPLATE_PATTERN.fullmatch(seg):
            # Normalize the segment
            normalized = seg.replace("-", "_").lower()
            return normalized
    return ""


def get_http_action_suffix(method: str, path: str) -> str:
    """
    Determine the action suffix based on path and HTTP method.

    Uses path's last segment for special actions (sync, sign, etc.)
    Falls back to HTTP method name for standard operations.
    """
    # First, check if path ends with a known action
    path_action = get_action_from_path(path)
    if path_action:
        return path_action

    # Use the HTTP method name directly as the suffix
    return method


def get_transfer_action_suffix(path: str, current_id: str) -> str | None:
    """
    Check if path or current operationID contains upload/download keywords.

    Returns 'upload' or 'download' if found, None otherwise.
    """
    path_lower = path.lower()
    id_lower = current_id.lower()

    if "upload" in path_lower or "upload" in id_lower:
        return "upload"
    if "download" in path_lower or "download" in id_lower:
        return "download"

    return None


async def transform_operation_id(
    path: str,
    method: str,
    current_id: str,
    is_deprecated: bool,
) -> str:
    """
    Transform a single operation ID according to the rules.

    Rules:
    - If deprecated, prefix with 'deprecated_'
    - If contains pulp, include '_pulp_'
    - If contains version, include '_vN_'
    - If contains _ui, include '_ui_'
    - Deduplicate consecutive words
    - Remove noise words (api, plugin, pulp_ansible, default, template args)
    - If path or operationId contains 'upload'/'download', ensure suffix is present
    """
    parts: list[str] = []

    # Check for pulp
    if has_pulp_segment(path):
        parts.append("pulp")

    # Check for version
    version = extract_version(path)
    if version:
        parts.append(version)

    # Check for UI
    if has_ui_segment(path):
        parts.append("ui")

    # Extract feature area (the meaningful part of the path)
    feature_parts = extract_feature_area(path)

    # Get action suffix from path and HTTP method
    action = get_http_action_suffix(method, path)

    # Build the new ID
    # Combine parts with feature area
    all_parts = parts + feature_parts

    # If action is in feature_parts, don't duplicate
    if action and all_parts and all_parts[-1].lower() == action.lower():
        action = ""

    # Deduplicate consecutive words
    all_parts = deduplicate_words(all_parts)

    # Build final ID
    new_id = "_".join(all_parts)

    # Add action if not already present
    if action and not new_id.endswith(f"_{action}"):
        new_id = f"{new_id}_{action}" if new_id else action

    # Ensure upload/download suffix is present if path or operationId contains these words
    transfer_action = get_transfer_action_suffix(path, current_id)
    if transfer_action and not new_id.endswith(f"_{transfer_action}"):
        new_id = f"{new_id}_{transfer_action}"

    # Clean up multiple underscores
    new_id = re.sub(r"_+", "_", new_id)
    new_id = new_id.strip("_")

    # Add deprecated prefix if needed
    if is_deprecated:
        new_id = f"deprecated_{new_id}"

    # Ensure we have something
    if not new_id:
        # Fallback: use a simplified version of the current ID
        new_id = current_id.lower()
        for noise in NOISE_WORDS:
            new_id = new_id.replace(f"_{noise}_", "_")
            new_id = new_id.replace(f"{noise}_", "")
        new_id = re.sub(r"_+", "_", new_id)
        new_id = new_id.strip("_")

    return new_id


async def transform_all_operations(
    operations: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, dict[str, str]]:
    """Transform all operation IDs concurrently."""
    tasks = []
    task_info = []

    for path, methods in operations.items():
        for method, op_data in methods.items():
            task = transform_operation_id(
                path,
                method,
                op_data["operationId"],
                op_data["deprecated"],
            )
            tasks.append(task)
            task_info.append((path, method))

    results = await asyncio.gather(*tasks)

    transformed: dict[str, dict[str, str]] = {}
    for (path, method), new_id in zip(task_info, results):
        if path not in transformed:
            transformed[path] = {}
        transformed[path][method] = new_id

    return transformed


def get_disambiguation_suffix(path: str) -> str:
    """
    Get a suffix to disambiguate duplicate operation IDs.

    Uses path parameters if available, otherwise uses the last path fragment.
    """
    # First, try to use path parameters
    params = extract_path_parameters(path)
    if params:
        # Normalize parameter names (replace hyphens, etc.)
        normalized_params = [p.replace("-", "_").lower() for p in params]
        return "_".join(normalized_params)

    # No parameters, use the last path fragment
    last_fragment = get_last_path_fragment(path)
    if last_fragment:
        return last_fragment

    # Fallback to empty (will trigger numeric suffix later if still not unique)
    return ""


def ensure_unique_ids(
    transformed: dict[str, dict[str, str]],
    max_length: int = 64,
) -> dict[str, dict[str, str]]:
    """
    Ensure all operation IDs are unique.

    If duplicates exist, disambiguate using path parameters or last path fragment.
    Falls back to numeric suffixes only if path-based disambiguation fails.
    """
    # Collect all IDs and their locations
    id_locations: dict[str, list[tuple[str, str]]] = {}
    for path, methods in transformed.items():
        for method, op_id in methods.items():
            if op_id not in id_locations:
                id_locations[op_id] = []
            id_locations[op_id].append((path, method))

    # Find duplicates and resolve them with path-based disambiguation
    result: dict[str, dict[str, str]] = {}
    for path, methods in transformed.items():
        result[path] = {}
        for method, op_id in methods.items():
            locations = id_locations[op_id]
            if len(locations) > 1:
                # Need to disambiguate - use path parameters or last fragment
                suffix = get_disambiguation_suffix(path)
                if suffix:
                    new_id = f"{op_id}_{suffix}"
                    # Check length limit
                    if len(new_id) <= max_length:
                        result[path][method] = new_id
                    else:
                        # Truncate suffix to fit
                        available = max_length - len(op_id) - 1  # -1 for underscore
                        if available > 0:
                            result[path][method] = f"{op_id}_{suffix[:available]}"
                        else:
                            result[path][method] = op_id
                else:
                    result[path][method] = op_id
            else:
                result[path][method] = op_id

    # Check for remaining duplicates and resolve with numeric suffix as last resort
    seen: dict[str, int] = {}
    final_result: dict[str, dict[str, str]] = {}

    for path, methods in result.items():
        final_result[path] = {}
        for method, op_id in methods.items():
            if op_id in seen:
                seen[op_id] += 1
                final_result[path][method] = f"{op_id}_{seen[op_id]}"
            else:
                seen[op_id] = 1
                final_result[path][method] = op_id

    return final_result


def apply_transformed_ids(
    spec: dict[str, Any],
    transformed: dict[str, dict[str, str]],
) -> dict[str, Any]:
    """Apply transformed operation IDs back to the spec."""
    # Deep copy the spec
    result = json.loads(json.dumps(spec))

    paths = result.get("paths", {})
    for path, methods in transformed.items():
        if path in paths:
            for method, new_id in methods.items():
                if method in paths[path]:
                    paths[path][method]["operationId"] = new_id

    return result


def validate_spec(spec: dict[str, Any]) -> list[str]:
    """Validate the transformed spec for uniqueness issues."""
    errors = []
    seen_ids: dict[str, str] = {}

    paths = spec.get("paths", {})
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        for method in ("get", "post", "put", "patch", "delete", "head", "options"):
            if method in path_item and isinstance(path_item[method], dict):
                operation = path_item[method]
                op_id = operation.get("operationId")
                if op_id:
                    if op_id in seen_ids:
                        errors.append(
                            f"Duplicate operationId '{op_id}' at {path}:{method} "
                            f"(also at {seen_ids[op_id]})"
                        )
                    else:
                        seen_ids[op_id] = f"{path}:{method}"

    return errors


async def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python id_fix.py <input_file>", file=sys.stderr)
        print("Example: python id_fix.py galaxy.json > galaxy_fixed.json", file=sys.stderr)
        sys.exit(1)

    input_file = sys.argv[1]

    # Read input file
    with open(input_file, encoding="utf-8") as f:
        spec = json.load(f)

    # Extract operations
    operations = extract_operations(spec)

    # Transform operation IDs (async for potential parallelism)
    transformed = await transform_all_operations(operations)

    # Ensure uniqueness
    unique_transformed = ensure_unique_ids(transformed)

    # Apply transformed IDs to spec
    result_spec = apply_transformed_ids(spec, unique_transformed)

    # Validate
    errors = validate_spec(result_spec)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)

    # Output result
    print(json.dumps(result_spec, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
