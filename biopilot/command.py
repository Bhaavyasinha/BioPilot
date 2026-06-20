"""The unit that flows from planner -> validator -> executor.

A ``Command`` is a *structured* description of one tool invocation. It is never
a raw shell string. Keeping it structured is what lets the validator inspect
every flag and lets the executor run it without a shell (no shell-injection
surface).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Command:
    step_id: str
    tool: str                       # e.g. "bwa", "samtools", "bcftools"
    subcommand: str                 # e.g. "mem", "sort", "call"; "" if none
    args: list[str] = field(default_factory=list)
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    stdout_to: str | None = None    # capture stdout to this file, if the tool
                                    # writes its result to stdout
    description: str = ""

    def argv(self) -> list[str]:
        """The exact argument vector, ready for subprocess (no shell)."""
        parts = [self.tool]
        if self.subcommand:
            parts.append(self.subcommand)
        parts.extend(self.args)
        return parts

    def render(self) -> str:
        """Human-readable command line (for logs / Nextflow / manifest)."""
        line = " ".join(self.argv())
        if self.stdout_to:
            line += f" > {self.stdout_to}"
        return line

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
