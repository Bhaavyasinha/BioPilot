"""Layer 3 - the Validator. The research heart of BioPilot."""
from __future__ import annotations

import enum
from dataclasses import dataclass, field

from ..command import Command
from ..planner.catalog import TOOL_CATALOG
from .schemas import COMMAND_SCHEMAS, kind_of


class Severity(enum.Enum):
    ERROR = "error"
    WARNING = "warning"


_SHELL_METACHARS = set(";|&$`<>\n\r")
_DESTRUCTIVE = {"rm", "rmdir", "mkfs", "dd", "shutdown", "reboot", "mv",
                "chmod", "chown", ":(){:|:&};:", "curl", "wget", "sudo"}


@dataclass
class ValidationIssue:
    severity: Severity
    code: str
    message: str
    step_id: str = ""

    def __str__(self) -> str:
        loc = f"[{self.step_id}] " if self.step_id else ""
        return f"{self.severity.value.upper()}: {loc}{self.message} ({self.code})"


@dataclass
class ValidationReport:
    issues: list = field(default_factory=list)

    @property
    def errors(self):
        return [i for i in self.issues if i.severity is Severity.ERROR]

    @property
    def warnings(self):
        return [i for i in self.issues if i.severity is Severity.WARNING]

    @property
    def ok(self) -> bool:
        return not self.errors

    def add(self, sev, code, msg, step_id=""):
        self.issues.append(ValidationIssue(sev, code, msg, step_id))

    def to_dict(self):
        return {
            "ok": self.ok,
            "n_errors": len(self.errors),
            "n_warnings": len(self.warnings),
            "issues": [
                {"severity": i.severity.value, "code": i.code,
                 "message": i.message, "step_id": i.step_id}
                for i in self.issues
            ],
        }


class Validator:
    def __init__(self, workdir: str = "."):
        self.workdir = workdir

    def validate(self, command: Command) -> ValidationReport:
        r = ValidationReport()
        if command.tool in _DESTRUCTIVE or command.subcommand in _DESTRUCTIVE:
            r.add(Severity.ERROR, "destructive_command",
                  f"refusing destructive/non-catalog command {command.tool!r}",
                  command.step_id)
            return r
        self._check_known(command, r)
        if r.errors:
            return r
        flags_seen = self._check_flags(command, r)
        self._check_semantics(command, flags_seen, r)
        self._check_safety(command, r)
        return r

    def validate_plan(self, commands):
        merged = ValidationReport()
        for c in commands:
            merged.issues.extend(self.validate(c).issues)
        return merged

    def _check_known(self, c, r):
        if c.tool not in TOOL_CATALOG:
            r.add(Severity.ERROR, "unknown_tool",
                  f"tool {c.tool!r} is not in the catalog (possible hallucination)",
                  c.step_id)
            return
        if (c.tool, c.subcommand) not in COMMAND_SCHEMAS:
            r.add(Severity.ERROR, "unknown_subcommand",
                  f"{c.tool!r} has no subcommand {c.subcommand!r}", c.step_id)

    def _check_flags(self, c, r):
        schema = COMMAND_SCHEMAS[(c.tool, c.subcommand)]
        seen = {}
        positionals = []
        args = c.args
        i = 0
        while i < len(args):
            tok = args[i]
            if tok.startswith("--"):
                name, _, inline = tok.partition("=")
                if name not in schema.flags:
                    r.add(Severity.ERROR, "unknown_flag",
                          f"unknown flag {name!r} for `{c.tool} {c.subcommand}`",
                          c.step_id)
                    i += 1
                    continue
                if schema.flags[name]:
                    val = inline if inline else (args[i + 1] if i + 1 < len(args) else None)
                    if val is None:
                        r.add(Severity.ERROR, "missing_value",
                              f"flag {name!r} expects a value", c.step_id)
                    else:
                        seen[name] = val
                        if not inline:
                            i += 1
                else:
                    seen[name] = True
                i += 1
            elif tok.startswith("-") and len(tok) > 1 and not _looks_numeric(tok):
                j = 1
                consumed_value = False
                while j < len(tok):
                    f = "-" + tok[j]
                    if f not in schema.flags:
                        r.add(Severity.ERROR, "unknown_flag",
                              f"unknown flag {f!r} for `{c.tool} {c.subcommand}`",
                              c.step_id)
                        j += 1
                        continue
                    if schema.flags[f]:
                        rest = tok[j + 1:]
                        if rest:
                            seen[f] = rest
                        elif i + 1 < len(args):
                            seen[f] = args[i + 1]
                            consumed_value = True
                        else:
                            r.add(Severity.ERROR, "missing_value",
                                  f"flag {f!r} expects a value", c.step_id)
                        break
                    else:
                        seen[f] = True
                        j += 1
                if consumed_value:
                    i += 1
                i += 1
            else:
                positionals.append(tok)
                i += 1

        if len(positionals) < schema.min_positional:
            r.add(Severity.ERROR, "missing_positional",
                  f"`{c.tool} {c.subcommand}` needs >= {schema.min_positional} "
                  f"positional argument(s), got {len(positionals)}", c.step_id)
        return seen

    def _check_semantics(self, c, flags, r):
        ref = flags.get("-f")
        if isinstance(ref, str) and kind_of(ref) not in (None, "fasta"):
            r.add(Severity.ERROR, "wrong_file_kind",
                  f"-f expects a FASTA reference, got {ref!r} ({kind_of(ref)})",
                  c.step_id)
        if (c.tool, c.subcommand) == ("bcftools", "call"):
            bad = [p for p in c.inputs if kind_of(p) in ("fastq", "fasta", "sam")]
            if bad:
                r.add(Severity.ERROR, "stage_mismatch",
                      f"bcftools call fed {bad} -- expected a pileup (.bcf/.vcf)",
                      c.step_id)
        if (c.tool, c.subcommand) == ("bcftools", "mpileup"):
            bad = [p for p in c.inputs if kind_of(p) == "fastq"]
            if bad:
                r.add(Severity.ERROR, "stage_mismatch",
                      f"bcftools mpileup fed raw FASTQ {bad} -- expected a BAM",
                      c.step_id)

    def _check_safety(self, c, r):
        if c.tool in _DESTRUCTIVE or c.subcommand in _DESTRUCTIVE:
            r.add(Severity.ERROR, "destructive_command",
                  f"refusing destructive/non-catalog command {c.tool!r}", c.step_id)
        for tok in [c.tool, c.subcommand, *c.args, *(c.outputs or []),
                    *(([c.stdout_to]) if c.stdout_to else [])]:
            if tok and any(ch in _SHELL_METACHARS for ch in tok):
                r.add(Severity.ERROR, "shell_metacharacter",
                      f"token {tok!r} contains a shell metacharacter -- blocked",
                      c.step_id)
            if tok and ".." in tok.split("/"):
                r.add(Severity.WARNING, "path_traversal",
                      f"token {tok!r} contains a parent-directory reference",
                      c.step_id)
        outs = set(c.outputs or []) | ({c.stdout_to} if c.stdout_to else set())
        clobber = outs & set(c.inputs)
        if clobber:
            r.add(Severity.ERROR, "input_clobber",
                  f"output(s) {sorted(clobber)} would overwrite an input", c.step_id)


def _looks_numeric(tok: str) -> bool:
    try:
        float(tok)
        return True
    except ValueError:
        return False
