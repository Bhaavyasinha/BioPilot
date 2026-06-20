"""Layer 5 - Provenance Recorder.

Every run emits a manifest that makes the analysis reproducible by anyone:
the original prompt, the parsed intent, the validated plan (every command),
pinned tool versions + container images, SHA-256 checksums of every input and
output, timing, and the validation report. The manifest *is* the scientific
artifact -- hand it to a colleague and they can reproduce the result exactly.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timezone

from ..command import Command
from ..intent.schema import Intent
from ..planner.catalog import TOOL_CATALOG


def sha256_file(path: str, _bufsize: int = 1 << 20) -> str | None:
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(_bufsize):
            h.update(chunk)
    return h.hexdigest()


class ProvenanceRecorder:
    def __init__(self, workdir: str = "."):
        self.workdir = workdir
        self.started = datetime.now(timezone.utc)

    def build(self, *, intent: Intent, commands: list[Command],
              validation: dict, step_results: list | None = None,
              tool_versions: dict[str, str] | None = None) -> dict:
        inputs = sorted({p for c in commands for p in c.inputs})
        outputs = sorted({p for c in commands for p in
                          (list(c.outputs) + ([c.stdout_to] if c.stdout_to else []))})

        manifest = {
            "biopilot_version": _bp_version(),
            "generated_utc": self.started.isoformat(),
            "completed_utc": datetime.now(timezone.utc).isoformat(),
            "request": {
                "prompt": intent.raw_prompt,
                "intent": intent.to_dict(),
            },
            "environment": {
                "python": sys.version.split()[0],
                "platform": platform.platform(),
            },
            "tool_catalog": {
                name: {"version": s.version, "container": s.container}
                for name, s in TOOL_CATALOG.items()
            },
            "resolved_tool_versions": tool_versions or {},
            "plan": [
                {
                    "step_id": c.step_id,
                    "command": c.render(),
                    "tool": c.tool,
                    "subcommand": c.subcommand,
                    "container": TOOL_CATALOG[c.tool].container if c.tool in TOOL_CATALOG else None,
                }
                for c in commands
            ],
            "validation": validation,
            "inputs": [{"path": p, "sha256": sha256_file(p)} for p in inputs],
            "outputs": [{"path": p, "sha256": sha256_file(p)} for p in outputs],
        }
        if step_results is not None:
            manifest["execution"] = [
                {"step_id": r.step_id, "command": r.command,
                 "returncode": r.returncode, "seconds": r.seconds,
                 "outputs": r.outputs}
                for r in step_results
            ]
        return manifest

    def write(self, manifest: dict, json_path: str, md_path: str | None = None) -> None:
        with open(json_path, "w") as f:
            json.dump(manifest, f, indent=2)
        if md_path:
            with open(md_path, "w") as f:
                f.write(self.render_markdown(manifest))

    @staticmethod
    def render_markdown(m: dict) -> str:
        lines = ["# BioPilot reproducibility manifest", ""]
        lines.append(f"- **BioPilot:** {m['biopilot_version']}")
        lines.append(f"- **Generated (UTC):** {m['generated_utc']}")
        lines.append(f"- **Prompt:** {m['request']['prompt']!r}")
        lines.append(f"- **Analysis:** {m['request']['intent']['analysis']}")
        v = m["validation"]
        lines.append(f"- **Validation:** {'PASSED' if v['ok'] else 'FAILED'} "
                     f"({v['n_errors']} errors, {v['n_warnings']} warnings)")
        lines.append("")
        lines.append("## Pipeline steps")
        lines.append("")
        for i, step in enumerate(m["plan"], 1):
            lines.append(f"{i}. `{step['command']}`")
            if step["container"]:
                lines.append(f"   - container: `{step['container']}`")
        lines.append("")
        lines.append("## Inputs (sha256)")
        lines.append("")
        for f_ in m["inputs"]:
            lines.append(f"- `{os.path.basename(f_['path'])}` — `{f_['sha256']}`")
        lines.append("")
        lines.append("## Outputs (sha256)")
        lines.append("")
        for f_ in m["outputs"]:
            lines.append(f"- `{os.path.basename(f_['path'])}` — `{f_['sha256']}`")
        lines.append("")
        return "\n".join(lines)


def _bp_version() -> str:
    try:
        from .. import __version__
        return __version__
    except Exception:
        return "0.0.0"


def collect_tool_versions(env_path: str | None = None) -> dict[str, str]:
    """Best-effort capture of the actual tool versions present at run time."""
    import subprocess
    env = dict(os.environ)
    if env_path:
        env["PATH"] = env_path + os.pathsep + env.get("PATH", "")
    out = {}
    for tool, args in (("bwa", []), ("samtools", ["--version"]),
                       ("bcftools", ["--version"])):
        try:
            p = subprocess.run([tool, *args], capture_output=True, text=True, env=env)
            text = (p.stdout + p.stderr).strip().splitlines()
            out[tool] = next((l for l in text if l.strip()), "")
        except Exception as e:
            out[tool] = f"unavailable: {e}"
    return out
