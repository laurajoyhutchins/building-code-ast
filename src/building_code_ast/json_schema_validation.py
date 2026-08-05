"""Small deterministic wrapper around JSON Schema Draft 2020-12 validation."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator


def validate_instances(
    instances: Sequence[Any], schema: Mapping[str, Any]
) -> list[dict[str, Any]]:
    validator = Draft202012Validator(schema)
    errors: list[dict[str, Any]] = []
    for index, instance in enumerate(instances):
        for error in sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path)):
            errors.append(
                {
                    "instance_index": index,
                    "instance_path": list(error.absolute_path),
                    "schema_path": list(error.absolute_schema_path),
                    "message": error.message,
                }
            )
    return errors
