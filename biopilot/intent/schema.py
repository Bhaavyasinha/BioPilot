"""The structured intermediate representation (IR).

The LLM never emits shell. It emits an ``Intent`` (this schema). Forcing the
model through a constrained, machine-checkable JSON object is the *first* half
of BioPilot's anti-hallucination defense: an intent that fails schema
validation never reaches the planner, let alone the shell.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

import jsonschema

# Analyses BioPilot currently knows how to plan. The LLM must pick one of
# these; it cannot invent an analysis type.
SUPPORTED_ANALYSES = ("variant_calling",)

INTENT_JSON_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "BioPilotIntent",
    "type": "object",
    "additionalProperties": False,
    "required": ["analysis", "inputs", "reference"],
    "properties": {
        "analysis": {
            "type": "string",
            "enum": list(SUPPORTED_ANALYSES),
            "description": "Which curated workflow to run.",
        },
        "inputs": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "string"},
            "description": "Sequencing read files (FASTQ).",
        },
        "reference": {
            "type": "string",
            "description": "Reference genome FASTA path or known id.",
        },
        "options": {
            "type": "object",
            "additionalProperties": True,
            "description": "Analysis-specific knobs (e.g. run_qc, ploidy).",
        },
        "raw_prompt": {
            "type": "string",
            "description": "The original natural-language request (for provenance).",
        },
    },
}


@dataclass
class Intent:
    analysis: str
    inputs: list[str]
    reference: str
    options: dict[str, Any] = field(default_factory=dict)
    raw_prompt: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Intent":
        return cls(
            analysis=d["analysis"],
            inputs=list(d["inputs"]),
            reference=d["reference"],
            options=dict(d.get("options", {})),
            raw_prompt=d.get("raw_prompt", ""),
        )


class IntentValidationError(ValueError):
    """Raised when an LLM-produced intent does not satisfy the schema."""


def validate_intent(d: dict[str, Any]) -> Intent:
    """Validate a raw dict against the JSON schema and return an Intent.

    This is a hard gate: a malformed or hallucinated intent stops here.
    """
    try:
        jsonschema.validate(d, INTENT_JSON_SCHEMA)
    except jsonschema.ValidationError as e:
        raise IntentValidationError(f"intent failed schema validation: {e.message}") from e
    return Intent.from_dict(d)
